"""
Utility module for git tree-rewrites.
"""

import multiprocessing
import os
import sys
import math
import time

import asyncio
from concurrent.futures import ProcessPoolExecutor

from collections import namedtuple
from subprocess import Popen, PIPE
from itertools import chain

import pygit2


DISPATCH = {
    'blob': 'rewrite_file',
    'tree': 'rewrite_tree',
    'commit': 'rewrite_commit',
}


class Repository:

    """Pickleable proxy for pygit2.Repository."""

    def __init__(self, path):
        self._repo = pygit2.Repository(path)

    def __getattr__(self, key):
        return getattr(self._repo, key)

    def __getitem__(self, key):
        return self._repo[key]

    def __getstate__(self):
        return self._repo.path

    def __setstate__(self, path):
        self._repo = pygit2.Repository(path)


class Signature:

    """Pickleable proxy for pygit2.Signature."""

    def __init__(self, sig):
        self._sig = sig

    def __getattr__(self, key):
        return getattr(self._sig, key)

    def __getstate__(self):
        sig = self._sig
        return sig.name, sig.email, sig.time, sig.offset

    def __setstate__(self, args):
        self._sig = pygit2.Signature(*args)


class AsyncQueue:

    def __init__(self, size, cb=None):
        self.jobs = ()
        self.size = size
        self.done = asyncio.Event()
        self.num_pending = 0
        self.num_active = 0
        self.num_total = 0
        self.num_done = 0
        self.status_callback = cb or (lambda q: None)

    def enqueue(self, num, jobs):
        self.num_pending += num
        self.num_total += num
        self.jobs = chain.from_iterable((self.jobs, jobs))
        for _ in range(self.size - self.num_active):
            self._start()
        return self

    def _start(self):
        try:
            job = next(self.jobs)
        except StopIteration:
            return
        future = asyncio.ensure_future(job)
        future.add_done_callback(self._finished)
        self.num_active += 1
        self.num_pending -= 1

    def _finished(self, future):
        self.num_active -= 1
        self.num_done += 1
        self._start()
        if not self.num_active:
            self.done.set()
        self.status_callback(self)

    def __await__(self):
        # NOTE: can't use `async def __await` nor return `self.done.wait()`
        # directly for some weird type requirements…
        yield from self.done.wait()


async def process_objects(size, func, objs):

    start = time.time()
    def status(queue):
        done, pending = queue.num_done, queue.num_total
        passed = time.time() - start
        rate = passed / done
        eta = (pending - done) * rate
        print('\r\033[K{} / {} objects rewritten ({:.1f} objs/sec) in {}, ETA: {}'
                .format(done, pending, 1 / rate,
                        time_to_str(passed), time_to_str(eta)),
                end='')
        sys.stdout.flush()

    queue = AsyncQueue(size, status)
    await queue.enqueue(len(objs), map(func, objs))


class DirEntry(namedtuple('DirEntry', ['mode', 'kind', 'sha1', 'name'])):

    path = ''

    def child(self, mode, kind, sha1, name):
        obj = DirEntry(mode, kind, sha1, name)
        obj.path = (self.path and self.path + '/') + name
        return obj

    def __hash__(self):
        # Can't use DirEntry.__hash__ because it seems impossible to override
        # in multiprocessing scenarios (globals don't get transferred), even
        # subclassing seems to be broken…
        raise NotImplementedError


def communicate(args, text=None):
    text = text.encode('utf-8') if text else None
    proc = Popen(args, stdin=PIPE, stdout=PIPE)
    return proc.communicate(text)[0].decode('utf-8')


def read_tree(repo, sha1):
    """Iterate over tuples (mode, kind, sha1, name)."""
    return [(e.filemode, e.type, e.id.hex, e.name)
            for e in repo[sha1]]


def write_tree(repo, entries):
    """Create a tree and return the hash."""
    builder = repo.TreeBuilder()
    for e in entries:
        mode, kind, sha1, name = e[:4]
        builder.insert(name, sha1, mode)
    return builder.write().hex


def read_blob(repo, sha1):
    return repo[sha1].data


def write_blob(repo, text):
    return repo.create_blob(text).hex


def create_commit(repo, author, committer, message, tree, parents):
    return repo.create_commit(
        None, author._sig, committer._sig, message, tree, parents).hex


def cached(func):
    cache = dict()
    def wrapper(self, *args):
        key = self._hash(*args)
        if key not in cache:
            cache[key] = asyncio.ensure_future(func(self, *args))
        return cache[key]
    wrapper.__name__ = func.__name__
    return wrapper


def time_to_str(seconds):
    return time.strftime('%H:%M:%S', time.gmtime(math.ceil(seconds)))


def SECTION(title):
    print("\n\n"+title+"\n"+"="*len(title))


class TreeFilter(object):

    def __init__(self):
        self.gitdir = pygit2.discover_repository('.')
        self.objmap = os.path.join(self.gitdir, 'objmap')
        self.repo = Repository(self.gitdir)

    def rewrite_root(self, sha1):
        sha1 = sha1.strip()
        obj = self.repo[sha1]
        if obj.type == pygit2.GIT_OBJ_TREE:
            return self.rewrite_root_tree(sha1)
        # TODO: what about tags?
        return self.rewrite_root_commit(sha1)

    @cached
    async def rewrite_root_commit(self, sha1):
        commit = self.repo[sha1]
        ids = [commit.tree_id] + commit.parent_ids
        tree, *parents = await asyncio.gather(*[
            asyncio.ensure_future(self.rewrite_root(id.hex))
            for id in ids
        ])
        return await self.create_commit(
            Signature(commit.author), Signature(commit.committer),
            commit.message, tree, parents)

    @cached
    async def rewrite_root_tree(self, sha1):
        root = DirEntry(0o040000, 'tree', sha1, '')
        tree, = await self.rewrite_object(root)
        self.objmap_file.write('{} {}\n'.format(sha1, tree[2]))
        return tree[2]

    @cached
    async def rewrite_tree(self, obj):
        """Rewrite all folder items individually, recursive."""
        old_entries = list(await self.read_tree(obj.sha1))
        new_entries = list(await self.map_tree(obj, old_entries))
        if new_entries != old_entries:
            sha1 = await self.write_tree(new_entries)
        else:
            sha1 = obj.sha1
        return [(obj.mode, obj.kind, sha1, obj.name)]

    async def map_tree(self, obj, entries):
        results = await asyncio.gather(*[
            self.rewrite_object(obj.child(*entry))
            for entry in entries
        ])
        return [entry for entries in results for entry in entries]

    @cached
    def rewrite_object(self, obj):
        rewrite = getattr(self, DISPATCH.get(obj.kind, 'rewrite_fallback'))
        return rewrite(obj)

    async def rewrite_commit(self, obj):
        return [obj[:]]

    async def rewrite_fallback(self, obj):
        return [obj[:]]

    def depends(self, obj):
        # In general, we have to depend on all metadata + location
        return (obj[:], obj.path, obj.mode)

    def _hash(self, obj=None):
        return hash(self.depends(obj) if isinstance(obj, DirEntry) else obj)

    @classmethod
    def main(cls, args=None):
        if args is None:
            args = sys.argv[1:]

        if '--' in args:
            cut = args.index('--')
            args, refs = args[:cut], args[cut+1:]
            objs = communicate(['git', 'rev-list', *refs])
            objs = sorted(set(objs.splitlines()))
        else:
            objs = list(sys.stdin)
            refs = []

        size = 2*multiprocessing.cpu_count()
        pool = ProcessPoolExecutor(size)
        loop = asyncio.get_event_loop()
        loop.set_default_executor(pool)

        instance = cls(*args)
        instance.size = size
        future = asyncio.ensure_future(instance.filter(objs, refs))
        loop.run_until_complete(future)
        return future.result()

    async def filter(self, objs, refs):
        if os.path.exists(self.objmap):
            print("objmap already exists:", self.objmap)
            print("If there is no other rebase in progress, please clean up\n"
                  "this folder and retry.")
            return 1
        with open(self.objmap, 'wt') as f:
            self.objmap_file = f
            return (await self.filter_tree(objs) or
                    await self.filter_branch(refs))

    async def filter_tree(self, objs):
        SECTION("Rewriting trees")
        await process_objects(self.size, self.rewrite_root, objs)

    async def filter_branch(self, refs):
        if not refs:
            return 0
        # NOTE: Since commit rewriting is fully sequential by nature, we could
        # just as well do this in a normal python function. It's done in a
        # coroutine here just for consistency.
        # NOTE: The two phases (commit/tree rewrites) have been merged into
        # one thereby effectively making use of parallelization for the commit
        # rewrites as well. However, I'm keeping the code for the second phase
        # here, so it can be invoked independently:
        SECTION("Rewriting commits")
        revs = communicate(['git', 'rev-list', '--reverse', *refs])
        revs = revs.splitlines()
        await process_objects(self.size, self.rewrite_root, revs)

        SECTION("Updating refs")
        for short in refs:
            refs = communicate(['git', 'rev-parse', '--symbolic-full-name', short])
            for ref in refs.splitlines():
                old = self.repo.revparse_single(ref)
                new = await self.rewrite_root(old.hex)
                if old == new:
                    print("WARNING: Ref {!r} is unchanged".format(ref))
                else:
                    self.repo.references[ref].set_target(new, "tree-filter")
                    print("Ref {!r} was rewritten".format(ref))
        return 0

    def read_tree(self, sha1):
        """Iterate over tuples (mode, kind, sha1, name)."""
        return self.run_in_executor(read_tree, self.repo, sha1)

    def write_tree(self, entries):
        """Create a tree and return the hash."""
        return self.run_in_executor(write_tree, self.repo, entries)

    def read_blob(self, sha1):
        return self.run_in_executor(read_blob, self.repo, sha1)

    def write_blob(self, text):
        return self.run_in_executor(write_blob, self.repo, text)

    def create_commit(self, *args):
        return self.run_in_executor(create_commit, self.repo, *args)

    def run_in_executor(self, fn, *args):
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, fn, *args)
