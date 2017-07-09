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

from .tree_filter import TreeFilter, cached

import os


def extract(sha1):
    cmd = "git cat-file blob {} | gunzip | git hash-object -w -t blob --stdin"
    return os.popen(cmd.format(sha1)).read().strip()


class Unpack(TreeFilter):

    def __init__(self, ext='.gz', unz='gunzip'):
        super().__init__()
        self.ext = ext
        self.unz = unz

    # rewrite depends only on the object payload and name:
    def depends(self, obj):
        return (obj.sha1, obj.name, obj.mode)

    @cached
    async def rewrite_file(self, obj):
        mode, kind, sha1, name = obj
        if name == '.gitattributes':
            text = obj.sha1 and await self.read_blob(obj.sha1) or b""
            sha1 = await self.write_blob("\n".join(
                fix_gitattr_line(line, self.ext)
                for line in text.decode('utf-8').splitlines()
            ).encode('utf-8'))
        elif name.endswith(self.ext):
            name, ext = os.path.splitext(name)
            sha1 = await self.run_in_executor(extract, sha1)
        return [(mode, kind, sha1, name)]


def fix_gitattr_line(line, ext):
    name, attr = line.split(' ', 1)
    if name.endswith(ext):
        return name[:-len(ext)] + ' ' + attr
    return line


main = Unpack.main
if __name__ == '__main__':
    import sys; sys.exit(main())
