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
        return (obj.sha1, obj.name)

    @cached
    def rewrite_file(self, obj):
        mode, kind, sha1, name = obj
        if obj.path in self.files:
            return []
        if name == '.gitattributes':
            text = obj.sha1 and self.read_blob(obj.sha1) or ""
            sha1 = self.write_blob("\n".join(
                line for line in text.splitlines()
                for name, attr in [line.split(' ', 1)]
                if name not in self.files))
        return [(mode, kind, sha1, name)]


main = Rm.main
if __name__ == '__main__':
    import sys; sys.exit(main())
