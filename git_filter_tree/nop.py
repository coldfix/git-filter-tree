"""
Module that should (slowly) do nothing on your repo!
"""

from git_filter_tree.tree_filter import TreeFilter


class NOP(TreeFilter):

    def rewrite_file(self, obj):
        return [obj[:]]


main = NOP.main
if __name__ == '__main__':
    import sys; sys.exit(main())
