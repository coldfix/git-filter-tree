"""
Utility module for git tree-rewrites.
"""

import multiprocessing
import os
import sys
import time

import asyncio
from concurrent.futures import ProcessPoolExecutor

from collections import namedtuple
from subprocess import Popen, PIPE, call
from itertools import starmap


DISPATCH = {
    'blob': 'rewrite_file',
    'tree': 'rewrite_tree',
    'commit': 'rewrite_commit',
}


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


def read_tree(sha1):
    """Iterate over tuples (mode, kind, sha1, name)."""
    cmd = "git ls-tree {}"
    return [line.rstrip('\r\n').split(maxsplit=3)
            for line in os.popen(cmd.format(sha1.strip()))]


def write_tree(entries):
    """Create a tree and return the hash."""
    text = '\n'.join(starmap('{0} {1} {2}\t{3}'.format, entries))
    args = ['git', 'mktree']
    return communicate(args, text).strip()


def read_blob(sha1):
    args = ['git', 'cat-file', 'blob', sha1.strip()]
    return communicate(args, None)


def write_blob(text):
    args = ['git', 'hash-object', '-w', '-t', 'blob', '--stdin']
    return communicate(args, text).strip()


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
    return time.strftime('%H:%M:%S', time.gmtime(seconds))


def SECTION(title):
    print("\n\n"+title+"\n"+"="*len(title))


class TreeFilter(object):

    def __init__(self):
        self.gitdir = communicate(['git', 'rev-parse', '--git-dir']).strip()
        self.gitdir = os.path.abspath(self.gitdir)
        self.objmap = os.path.join(self.gitdir, 'objmap')

    @cached
    async def rewrite_root(self, sha1):
        sha1 = sha1.strip()
        root = DirEntry('040000', 'tree', sha1, '')
        tree, = await self.rewrite_object(root)
        with open(os.path.join(self.objmap, sha1), 'w') as f:
            f.write(tree[2])
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
        # TODO: query multiple entries at once?
        return [entry for m, k, s, n in entries
                for entry in await self.rewrite_object(obj.child(m, k, s, n))]

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
        return (obj[:], obj.path)

    def _hash(self, obj=None):
        return hash(self.depends(obj) if isinstance(obj, DirEntry) else obj)

    @classmethod
    def main(cls, args=None):
        if args is None:
            args = sys.argv[1:]

        if '--' in args:
            cut = args.index('--')
            args, refs = args[:cut], args[cut+1:]
            instance = cls(*args)

            trees = communicate(['git', 'log', '--format=%T'] + refs)
            trees = sorted(set(trees.splitlines()))
            return (instance.filter_tree(trees) or
                    instance.filter_branch(refs))

        else:
            instance = cls(*args)
            return instance.filter_tree()

    def filter_tree(self, trees=None):
        if trees is None:
            trees = list(sys.stdin)

        try:
            os.makedirs(self.objmap)
        except FileExistsError:
            print("objmap already exists:", self.objmap)
            print("If there is no other rebase in progress, please clean up\n"
                  "this folder and retry.")
            return 1

        SECTION("Rewriting trees (parallel)")

        size = 2*multiprocessing.cpu_count()
        self.pool = ProcessPoolExecutor(size)

        loop = asyncio.get_event_loop()
        loop.set_default_executor(self.pool)

        pending = len(trees)
        done = 0
        start = time.time()

        async def rewrite_roottree(tree):
            await self.rewrite_root(tree)
            nonlocal done
            done += 1
            passed = time.time() - start
            rate = passed / done
            eta = (pending - done) * rate
            print('\r\033[K{} / {} Trees rewritten ({:.1f} trees/sec) in {}, ETA: {}'
                  .format(done, pending, 1 / rate,
                          time_to_str(passed), time_to_str(eta)),
                  end='')
            sys.stdout.flush()

        loop.run_until_complete(asyncio.wait([
            rewrite_roottree(tree)
            for tree in trees
        ]))

        return 0

    def filter_branch(self, refs):
        SECTION("Rewriting commits (sequential)")
        call([
            'git', 'filter-branch', '--commit-filter',
            'obj=$1 && shift && git commit-tree $(cat $objmap/$obj) "$@"',
            '--'] + refs,
             env={'objmap': self.objmap})

    def read_tree(self, sha1):
        """Iterate over tuples (mode, kind, sha1, name)."""
        return self.run_in_executor(read_tree, sha1)

    def write_tree(self, entries):
        """Create a tree and return the hash."""
        return self.run_in_executor(write_tree, entries)

    def read_blob(self, sha1):
        return self.run_in_executor(read_blob, sha1)

    def write_blob(self, text):
        return self.run_in_executor(write_blob, text)

    def run_in_executor(self, fn, *args):
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, fn, *args)
