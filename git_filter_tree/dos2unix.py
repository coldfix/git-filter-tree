"""
History rewrite helper script: Convert files to unix line endings, and remove
                               trailing spaces from them, in history

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
        if len(text) == 0 or text[-1] == b'\n' and (len(text) == 1 or text[-2] != b'\n') and text.find(b"\r") == -1 and text.find(b" \n") == -1:
            return obj.sha1
        lines = text.splitlines()
        while len(lines) > 0 and lines[-1].rstrip() == b"":
            lines.pop()
        if len(lines) > 0:
            content =  b"\n".join(map(bytes.rstrip, lines)) + b"\n"
        else:
            content = b""
        return await self.write_blob(content)

main = Dos2Unix.main
if __name__ == '__main__':
    import sys; sys.exit(main())
