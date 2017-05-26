#!/usr/bin/env python
from tree_filter import read_tree, write_tree, cached, rewrite_trees


def rewrite_roottree(sha1):
    return rewrite_object('040000', 'tree', sha1.strip(), '')


@cached
def rewrite_object(mode, kind, sha1, name):
    sha1 = sha1.strip()
    rewrite = rewrite_file if kind == 'blob' else rewrite_tree
    new_entries = rewrite(mode, kind, sha1, name)
    with open('objmap/'+sha1, 'w') as f:
        for new_mode, new_kind, new_sha1, new_name in new_entries:
            f.write(new_sha1+'\n')
    return new_entries


def rewrite_tree(mode, kind, sha1, name):
    old_entries = list(read_tree(sha1))
    new_entries = [new_entry
                   for old_entry in old_entries
                   for new_entry in rewrite_object(*old_entry)]
    if old_entries != new_entries:
        sha1 = write_tree(new_entries)
    return [(mode, kind, sha1, name)]


def rewrite_file(mode, kind, sha1, name):
    if not name.endswith('.ref.gz'):
        return [(mode, kind, sha1, name)]
    base, ext = os.path.splitext(name)
    cmd = "git cat-file -p {} | gunzip | git hash-object -w -t blob --stdin"
    sha1 = os.popen(cmd.format(sha1)).read().strip()
    return [(mode, kind, sha1, base)]



if __name__ == '__main__':
    sys.exit(rewrite_trees(rewrite_roottree, list(sys.stdin)))
