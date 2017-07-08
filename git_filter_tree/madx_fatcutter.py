"""
Module used for the MAD-X migration from SVN to git.

Combines `unpack` and `rm` filter with one exception for unpacking.
"""

from git_filter_tree.tree_filter import TreeFilter, cached

import os


REMOVE = {
    'doc/latexuguide/madxuguide.pdf',
    'doc/latexuguide/uguide50209.pdf',
    'doc/mad8usrguide/maduser.pdf',
    'doc/physguide/madx-twiss_notes.pdf',
    'doc/usrguide/reports/reference.pdf',
    'doc/usrguide/reports/reference.ps',
    #'tools/numdiff/doc/CERN-ACC-NOTE-2013-0005.pdf',
}

EXT = '.gz'


def shall_extract(name):
    return (name.endswith(EXT) and
            name != 'tests/test-hllhc/last_twiss.20.ref.gz')


class FatCutter(TreeFilter):

    # rewrite depends only on the object payload and name:
    def depends(self, obj):
        return (obj.sha1, obj.path)

    @cached
    def rewrite_file(self, obj):
        if obj.path in REMOVE:
            return []
        mode, kind, sha1, name = obj
        if name == '.gitattributes':
            text = obj.sha1 and self.read_blob(obj.sha1) or b""
            sha1 = self.write_blob("\n".join(
                fix_gitattr_line(line)
                for line in text.decode('utf-8').splitlines()
                for name, attr in [line.split(' ', 1)]
                if name not in REMOVE
            ).encode('utf-8'))
        elif shall_extract(obj.path):
            name, ext = os.path.splitext(name)
            cmd = "git cat-file blob {} | gunzip | git hash-object -w -t blob --stdin"
            sha1 = os.popen(cmd.format(sha1)).read().strip()
        return [(mode, kind, sha1, name)]


def fix_gitattr_line(line):
    name, attr = line.split(' ', 1)
    if shall_extract(name):
        return name[:-len(EXT)] + ' ' + attr
    return line


main = FatCutter.main
if __name__ == '__main__':
    import sys; sys.exit(main())
