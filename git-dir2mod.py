#!/usr/bin/env python
from tree_filter import read_tree, write_tree, cached, rewrite_trees


@cached
def gitmodules_file():
    sha1 = write_blob("""
[submodule "madx-examples"]
	path = examples
	url = https://github.com/MethodicalAcceleratorDesign/madx-examples.git
"""[1:])
    return ('100644', 'blob', sha1, '.gitmodules')


def rewrite_object(mode, kind, sha1, name):
    if kind == 'tree' and name == 'examples':
        return rewrite_tree(mode, kind, sha1, name)
    return [(mode, kind, sha1, name)]


@cached
def rewrite_tree(mode, kind, sha1, name):
    commit = open('../treemap/'+sha1).read().strip()
    return [
        ('160000', 'commit', commit, name),
        gitmodules_file(),
    ]


def rewrite_roottree(sha1):
    sha1 = sha1.strip()
    old_entries = list(read_tree(sha1))
    new_entries = [new_entry
                   for old_entry in old_entries
                   for new_entry in rewrite_object(*old_entry)]
    if old_entries != new_entries:
        new_sha1 = write_tree(new_entries)
    with open('objmap/'+sha1, 'w') as f:
        f.write(new_sha1)
    return new_sha1


if __name__ == '__main__':
    sys.exit(rewrite_trees(rewrite_roottree, list(sys.stdin)))
