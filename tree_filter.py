"""
Utility module for git tree-rewrites.
"""

import multiprocessing
import os
import sys
import time

from subprocess import Popen, PIPE
from itertools import starmap


def communicate(args, text=None):
    text = text.encode('utf-8') if text else None
    proc = Popen(args, stdin=PIPE, stdout=PIPE)
    return proc.communicate(text)[0].decode('utf-8')


def read_tree(sha1):
    """Iterate over tuples (mode, kind, sha1, name)."""
    cmd = "git ls-tree {}"
    return (line.rstrip('\r\n').split(maxsplit=3)
            for line in os.popen(cmd.format(sha1.strip())))


def write_tree(entries):
    """Create a tree and return the hash."""
    #print(list(entries))
    text = '\n'.join(starmap('{} {} {}\t{}'.format, entries))
    args = ['git', 'mktree']
    return communicate(args, text).strip()


def write_blob(text):
    args = ['git', 'hash-object', '-w', '-t', 'blob', '--stdin']
    return communicate(args, text).strip()


def cached(func):
    cache = multiprocessing.Manager().dict()
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    return wrapper


def time_to_str(seconds):
    return time.strftime('%H:%M:%S', time.gmtime(seconds))


def rewrite_trees(rewrite_roottree, trees):
    os.makedirs('objmap', exist_ok=True)

    pool = multiprocessing.Pool(2*multiprocessing.cpu_count())

    pending = len(trees)
    done = 0
    tstart = time.time()
    checkpoint_done = 0
    checkpoint_time = tstart

    for _ in pool.imap_unordered(rewrite_roottree, trees):
    #for _ in map(rewrite_roottree, trees):
        done += 1
        now = time.time()
        done_since_checkpoint = done - checkpoint_done
        compl_rate = (now - checkpoint_time) / done_since_checkpoint
        eta = time_to_str((pending - done) * compl_rate)
        print('\r{} / {} Trees rewritten ({:.1f} trees/sec), ETA: {}          '
                .format(done, pending, 1 / compl_rate, eta), end='')
        sys.stdout.flush()
        # Keep a window of the last 5s of rewrites for ETA calculation.
        if now - checkpoint_time > 5:
            checkpoint_done = done
            checkpoint_time = now

    pool.close()
    pool.join()

    elapsed = time.time() - tstart
    print('\nTree rewrite completed in {} ({:.1f} trees/sec)'
          .format(time_to_str(elapsed), done / elapsed), end='')
