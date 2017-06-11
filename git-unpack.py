#!/usr/bin/env python
"""
History rewrite helper script: Unzip files in history

Usage:
    ./git-unpack.py [EXT] [PROG]

Arguments:

    EXT         Filename extension          [default: .gz]
    PROG        Program to run for the file [default: gunzip]

Example:

    ./git-unpack.py .gz gunzip

This will leave you with with an `objmap` folder in the current directory
that maps top level trees to other the rewritten trees, i.e.

    echo NEW_SHA1 > objmap/OLD_SHA1
"""

from tree_filter import TreeFilter, cached

import os
import sys


class Unpack(TreeFilter):

    def __init__(self, ext='.gz', unz='gunzip'):
        self.ext = ext
        self.unz = unz

    @cached
    def rewrite_file(self, mode, kind, sha1, name):
        if not name.endswith(self.ext):
            return [(mode, kind, sha1, name)]
        base, ext = os.path.splitext(name)
        cmd = "git cat-file blob {} | {} | git hash-object -w -t blob --stdin"
        sha1 = os.popen(cmd.format(sha1, self.unz)).read().strip()
        return [(mode, kind, sha1, base)]


if __name__ == '__main__':
    Unpack(*sys.argv[1:]).main()
