"""
History rewrite helper script: Remove specific files (not dirs)

Usage:
    git-filter-tree rm PATH [PATH...] [-- REFS]

Arguments:

    PATH        Absolute filename within the repository
"""

from .tree_filter import TreeFilter, cached


class Rm(TreeFilter):

    def __init__(self, *files):
        super().__init__()
        self.files = set(files)

    # rewrite depends only on the object payload and name:
    def depends(self, obj):
        return (obj.sha1, obj.name, obj.mode)

    @cached
    async def rewrite_file(self, obj):
        mode, kind, sha1, name = obj
        if obj.path in self.files:
            return []
        if name == '.gitattributes':
            text = obj.sha1 and await self.read_blob(obj.sha1) or b""
            sha1 = await self.write_blob("\n".join(
                line for line in text.decode('utf-8').splitlines()
                for name, attr in [line.split(' ', 1)]
                if name not in self.files
            ).encode('utf-8'))
        return [(mode, kind, sha1, name)]


main = Rm.main
if __name__ == '__main__':
    import sys; sys.exit(main())
