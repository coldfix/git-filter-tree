#!/usr/bin/env python
"""
History rewrite helper script: Convert subfolder to submodule.

Usage:
    ./git-dir2mod.py TREEMAP FOLDER URL [NAME]

Arguments:

    TREEMAP     Path to tree index. For every top-level tree there should be
                a file $TREEMAP/$TREE_SHA1 that contains the SHA1 of the
                target commit.

    FOLDER      Subfolder to replace.

    URL         URL of the submodule

    NAME        Name of the submodule (defaults to FOLDER)

This will leave you with with an `objmap` folder in the current directory
that maps top level trees to other the rewritten trees, i.e.

    echo NEW_SHA1 > objmap/OLD_SHA1
"""

from tree_filter import TreeFilter, cached, write_blob

import os
import sys


class Dir2Mod(TreeFilter):

    def __init__(self, treemap, folder, url, name=None):
        self.treemap = treemap
        self.folder = folder
        self.url = url
        self.name = name or folder

    # TODO: nested path
    def rewrite_object(self, mode, kind, sha1, name):
        if kind == 'tree' and name == self.folder:
            return self.rewrite_tree(mode, kind, sha1, name)
        return [(mode, kind, sha1, name)]

    @cached
    def rewrite_tree(self, mode, kind, sha1, name):
        commit = open(os.path.join(self.treemap, sha1)).read().strip()
        return [
            ('160000', 'commit', commit, name),
            self.gitmodules_file(),
        ]

    # TODO: append to existing
    @cached
    def gitmodules_file(self):
        sha1 = write_blob("""
[submodule "{}"]
	path = {}
	url = {}
"""[1:].format(self.name, self.folder, self.url))
        return ('100644', 'blob', sha1, '.gitmodules')


if __name__ == '__main__':
    Dir2Mod(*sys.argv[1:]).main()
