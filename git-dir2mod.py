#!/usr/bin/env python
from tree_filter import TreeFilter, cached, write_blob


class Dir2Mod(TreeFilter):

    NAME = 'examples'
    PATH = 'examples'
    URL = 'https://github.com/MethodicalAcceleratorDesign/madx-examples.git'

    def rewrite_object(self, mode, kind, sha1, name):
        if kind == 'tree' and name == 'examples':
            return self.rewrite_tree(mode, kind, sha1, name)
        return [(mode, kind, sha1, name)]

    @cached
    def rewrite_tree(self, mode, kind, sha1, name):
        commit = open('../treemap/'+sha1).read().strip()
        return [
            ('160000', 'commit', commit, name),
            self.gitmodules_file(),
        ]

    @cached
    def gitmodules_file(self):
        sha1 = write_blob("""
[submodule "{}"]
	path = {}
	url = {}
"""[1:].format(self.NAME, self.PATH, self.URL))
        return ('100644', 'blob', sha1, '.gitmodules')


if __name__ == '__main__':
    Dir2Mod().main()
