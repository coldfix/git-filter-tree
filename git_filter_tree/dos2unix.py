"""
History rewrite helper script: Convert files to unix line endings in history

Usage:
    git-filter-tree dos2unix EXT [-- REFS]

Arguments:

    EXT         Filename extension          [default: .gz]
    REFS        git-rev-list options
"""

from .tree_filter import TreeFilter, cached

import os

class Dos2Unix(TreeFilter):

    def __init__(self, ext):
        super().__init__()
        self.ext = ext

    # rewrite depends only on the object payload and name:
    def depends(self, obj):
        return (obj.sha1, obj.name, obj.mode)

    @cached
    async def rewrite_file(self, obj):
        mode, kind, sha1, name = obj
        if name.endswith(self.ext):
            sha1 = await self.convertToUnix(obj)
        return [(mode, kind, sha1, name)]

    async def convertToUnix(self, obj):
        text = await self.read_blob(obj.sha1)
        lines = text.decode('utf-8').splitlines()
        while len(lines) > 0 and lines[-1] == '':
            lines.pop()
        if len(lines) > 0:
            content =  "\n".join(line.rstrip() for line in lines) + "\n"
        else:
            content = ""
        return await self.write_blob(content.encode('utf-8'))

main = Dos2Unix.main
if __name__ == '__main__':
    import sys; sys.exit(main())
