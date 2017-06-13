"""
History rewrite helper script: Convert subfolder to submodule.

Usage:
    git-filter-tree dir2mod TREEMAP FOLDER URL [NAME] [-- REFS]

Arguments:

    TREEMAP     Path to tree index. For every top-level tree there should be
                a file $TREEMAP/$TREE_SHA1 that contains the SHA1 of the
                target commit.
    FOLDER      Subfolder to replace.
    URL         URL of the submodule
    NAME        Name of the submodule (defaults to FOLDER)
    REFS        `git-rev-list` options
"""

from .tree_filter import TreeFilter, cached, write_blob, read_blob

import multiprocessing
import os


class Dir2Mod(TreeFilter):

    def __init__(self, treemap, folder, url, name=None):
        super().__init__()
        self.treemap = treemap
        self.folder = tuple(folder.split('/'))
        self.url = url
        self.name = name or folder
        self.has_folder = multiprocessing.Manager().dict()

    def depends(self, obj):
        return (obj.sha1, obj.path)

    @cached
    def rewrite_tree(self, obj):
        if obj.path == self.folder:
            self.has_folder[self._hash(obj)] = True
            commit = open(os.path.join(self.treemap, obj.sha1)).read().strip()
            return [('160000', 'commit', commit, obj.name)]
        # only recurse into `self.folder`:
        elif obj.path == self.folder[:len(obj.path)]:
            return super().rewrite_tree(obj)
        else:
            return [obj[:]]

    def map_tree(self, obj, entries):
        new_entries = super().map_tree(obj, entries)
        has_folder = self.has_folder.setdefault(self._hash(obj), any(
            self.has_folder.get(self._hash(obj.child(*item)))
            for item in entries
        ))
        if obj.parent is None and has_folder:
            i = next((i for i, e in enumerate(new_entries)
                      if e[3] == '.gitmodules'), None)
            if i is None:
                new_entries.append(self.gitmodules_file(None))
            else:
                new_entries[i] = self.gitmodules_file(new_entries[i][2])
        return new_entries

    @cached
    def gitmodules_file(self, sha1):
        text = sha1 and read_blob(sha1) or ""
        sha1 = write_blob(text + """
[submodule "{}"]
    path = {}
    url = {}
"""[1:].format(self.name, '/'.join(self.folder), self.url))
        return ('100644', 'blob', sha1, '.gitmodules')


main = Dir2Mod.main
if __name__ == '__main__':
    import sys; sys.exit(main())
