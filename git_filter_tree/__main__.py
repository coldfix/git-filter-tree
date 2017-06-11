import sys
from importlib import import_module

from os.path import dirname


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    if __file__:
        sys.path.append(dirname(dirname(__file__)))
    try:
        mod = import_module(args[0], "git_filter_tree")
    except ImportError:
        mod = import_module("git_filter_tree."+args[0], "git_filter_tree")
    return mod.main(args[1:])


if __name__ == '__main__':
    main()
