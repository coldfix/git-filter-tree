"""
History rewrite helper script: Unzip files in history

Usage:
    git-filter-tree unpack [EXT] [PROG] [-- REFS]

Arguments:

    EXT         Filename extension          [default: .gz]
    PROG        Program to run for the file [default: gunzip]
    REFS        git-rev-list options

See also: http://coldfix.de/2017/06/11/git-unpack
"""

from .tree_filter import TreeFilter, cached, read_blob, write_blob

import os


class Unpack(TreeFilter):

    def __init__(self, ext='.gz', unz='gunzip'):
        super().__init__()
        self.ext = ext
        self.unz = unz

    # rewrite depends only on the object payload and name:
    def depends(self, obj):
        return (obj.sha1, obj.name)

    @cached
    def rewrite_file(self, obj):
        mode, kind, sha1, name = obj
        if name == '.gitattributes':
            text = obj.sha1 and read_blob(obj.sha1) or ""
            sha1 = write_blob("\n".join(
                fix_gitattr_line(line, self.ext)
                for line in text.splitlines()))
        elif name.endswith(self.ext):
            name, ext = os.path.splitext(name)
            cmd = "git cat-file blob {} | {} | git hash-object -w -t blob --stdin"
            sha1 = os.popen(cmd.format(sha1, self.unz)).read().strip()
        return [(mode, kind, sha1, name)]


def fix_gitattr_line(line, ext):
    name, attr = line.split(' ', 1)
    if name.endswith(ext):
        return name[:-len(ext)] + ' ' + attr
    return line


main = Unpack.main
if __name__ == '__main__':
    import sys; sys.exit(main())
