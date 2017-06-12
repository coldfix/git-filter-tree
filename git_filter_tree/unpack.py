"""
History rewrite helper script: Unzip files in history

Usage:
    git-filter-tree unpack [EXT] [PROG] [-- REFS]

Arguments:

    EXT         Filename extension          [default: .gz]
    PROG        Program to run for the file [default: gunzip]
    REFS        git-rev-list options
"""

from .tree_filter import TreeFilter, cached

import os


class Unpack(TreeFilter):

    def __init__(self, ext='.gz', unz='gunzip'):
        super().__init__()
        self.ext = ext
        self.unz = unz

    # rewrite depends only on the object payload:
    def depends(self, obj):
        return obj.sha1

    @cached
    def rewrite_file(self, obj):
        mode, kind, sha1, name = obj
        if name.endswith(self.ext):
            name, ext = os.path.splitext(name)
            cmd = "git cat-file blob {} | {} | git hash-object -w -t blob --stdin"
            sha1 = os.popen(cmd.format(sha1, self.unz)).read().strip()
        return [(mode, kind, sha1, name)]


main = Unpack.main
if __name__ == '__main__':
    import sys; sys.exit(main())
