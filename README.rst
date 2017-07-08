git-filter-tree
---------------

|Tests| |License|

Utilities for efficient ``git`` history rewrites similar to (but ultimately
different from) ``git filter-branch --index-filter``.

The main conceptual difference to ``--index-filter`` is that any rewrite of a
tree must depend only on the tree itself, but not on the commit or its (new)
parents. This means that history rewrites can be split into

- rewriting trees
- rewriting commits

The tree rewrites can be **parallelized** and **cached**, which can make a
huge performance difference compared with ``--index-filter``.

See also `Large scale Git history rewrites`_.


Dependencies
~~~~~~~~~~~~

- python 3.5
- pygit2_ (tested with 0.25 and 0.26).

.. _pygit2: http://www.pygit2.org/


Usage
~~~~~

In general, in order to perform your own special rewrite, you will have to
implement a python module with a class deriving from the
``git_tree_filter.tree_filter.TreeFilter`` class. There are two example
modules in the source code, from which you may learn, or which may already fit
your needs.

unpack
~~~~~~

This module is designed to unpack all ``.gz`` files in the current repository.
However, it can be used to run arbitrary shell commands to all files of a
given extension. Usage:

.. code-block:: bash

    python3 git_tree_filter unpack [EXT] [COMMAND] -- --branches --tags

The given command will be called for each distinct file in the repo's history
that has the specified extension – with the file content on its STDIN and must
output the replacement file content on its STDOUT.

For more details, see `git unpack: efficient tree filter`_.

rm
~~

Remove a few specific files (not dirs) from repository. Usage:

.. code-block:: bash

    python3 git_tree_filter rm [PATH...] -- --branches --tags

dir2mod
~~~~~~~

This module is a helper to change the role of a subdirectory in a git repo to
a submodule.

For more details, see `git dir2mod: subdir to submodule`_.


.. References:

.. _`git unpack: efficient tree filter`: http://coldfix.de/2017/06/11/git-unpack
.. _`git dir2mod: subdir to submodule`: http://coldfix.de/2017/06/13/git-dir2mod
.. _Large scale Git history rewrites: https://www.bitleaks.net/blog/large-scale-git-history-rewrites/

.. Badges:

.. |Tests| image::     https://img.shields.io/travis/coldfix/git-filter-tree/master.svg
   :target:            https://travis-ci.org/coldfix/git-filter-tree
   :alt:               Build Status

.. |License| image::   https://img.shields.io/badge/License-GPLv3+-blue.svg
   :target:            https://github.com/coldfix/git-filter-tree/blob/master/COPYING.GPLv3.txt
   :alt:               GPLv3
