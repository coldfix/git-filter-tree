#!/usr/bin/env python
from tree_filter import TreeFilter, cached

import os


class UnpackGz(TreeFilter):

    @cached
    def rewrite_file(self, mode, kind, sha1, name):
        if not name.endswith('.ref.gz'):
            return [(mode, kind, sha1, name)]
        base, ext = os.path.splitext(name)
        cmd = "git cat-file blob {} | gunzip | git hash-object -w -t blob --stdin"
        sha1 = os.popen(cmd.format(sha1)).read().strip()
        return [(mode, kind, sha1, base)]


if __name__ == '__main__':
    UnpackGz().main()
