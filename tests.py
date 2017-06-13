
import tempfile
import subprocess
import unittest
import shutil
import os
from io import BytesIO
from gzip import GzipFile

import pygit2 as git


def gzip(name, data):
    sio = BytesIO()
    with GzipFile(name, 'wb', fileobj=sio) as f:
        f.write(data if isinstance(data, bytes) else data.encode('utf-8'))
    return bytes(sio.getbuffer())


def gunzip(name, data):
    sio = BytesIO(data)
    with GzipFile(name, 'rb', fileobj=sio) as f:
        return f.read()


def create_tree(repo, tree):
    builder = repo.TreeBuilder()
    for k, v in tree.items():
        if isinstance(v, (str, bytes)): o, m = repo.create_blob(v), git.GIT_FILEMODE_BLOB
        elif isinstance(v, dict):       o, m = create_tree(repo,v), git.GIT_FILEMODE_TREE
        elif isinstance(v, tuple):      o, m = v
        elif isinstance(v, git.Blob):   o, m = v, git.GIT_FILEMODE_BLOB
        elif isinstance(v, git.Tree):   o, m = v, git.GIT_FILEMODE_TREE
        elif isinstance(v, git.Commit): o, m = v, git.GIT_FILEMODE_COMMIT
        elif isinstance(v, git.Tag):    o, m = v, git.GIT_FILEMODE_TAG
        else:
            raise ValueError("Unsupported object: {}".format(v))
        builder.insert(k, o, m)
    return builder.write()


def log(path, branch):
    return subprocess.check_output([
        'git', '-C', path, 'log', '--reverse', '--format=%T %H %s', branch
    ]).decode('utf-8').splitlines()


class Branch:

    author = git.Signature('Lord Buckethead', 'lord@bucket.head')
    committer = author

    def __init__(self, repo, *head, name='refs/heads/master'):
        self.repo = repo
        self.head = head
        self.name = name

    def commit(self, title, tree, *merge):
        self.head = (self.repo.create_commit(
            self.name, self.author, self.committer,
            title, create_tree(self.repo, tree),
            list(self.head+merge)),)


def init_test_repo(path, bare=True):

    flags = git.GIT_REPOSITORY_INIT_NO_REINIT | git.GIT_REPOSITORY_INIT_MKPATH
    repo = git.init_repository(path, bare, flags)
    master = Branch(repo)

    ####
    tree = {'nested': {'subdir': {
        'large file': "large\n"*10000,
        'small file': "small*10000\n",
    }}}
    master.commit("Large and small test files", tree)

    ####
    subd = tree['nested']['subdir']
    subd['large file.gz'] = gzip("large file", subd.pop('large file'))
    subd['small file.gz'] = gzip("small file", subd.pop('small file'))
    master.commit("Not so big after all.", tree)

    ####
    tree['sibling'] = {'ûnïçoδΣ': "unique name\n"}
    master.commit("Add file with unicode name.", tree)

    ####
    subd['large file.gz'] = gzip("large file", "large\n2nd line\n"*10000)
    subd['small file.gz'] = gzip("small file", "1st line\nsmall*10000\n")
    master.commit("Modify the binary files.", tree)

    ####
    subd['small file'] = gunzip("small file", subd.pop('small file.gz'))
    master.commit("Extract the small file.\n\nBetter for diffs.", tree)
    return repo


class TestTreeFilter(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        self.path = tempfile.mkdtemp()
        self.repo = init_test_repo(self.path)

    def tearDown(self):
        shutil.rmtree(self.path)


    def check_same(self, repo_a, repo_b):
        branches_a = sorted(list(repo_a.branches.local))
        branches_b = sorted(list(repo_b.branches.local))
        self.assertEqual(branches_a, branches_b)

        # cross-check all branches for equality:
        for bra, brb in zip(branches_a, branches_b):
            commits_a = ["Branch: "+bra] + log(repo_a.path, bra)
            commits_b = ["Branch: "+brb] + log(repo_b.path, brb)
            self.assertEqual(commits_a, commits_b)

    def test_unpack_crossref(self):
        git_unpack = os.path.join(os.path.dirname(__file__), 'git-unpack')
        path_slow = tempfile.mkdtemp(prefix='git-unpack-')
        path_fast = tempfile.mkdtemp(prefix='git-unpack-')
        print("Slow:", path_slow)
        print("Fast:", path_fast)
        subprocess.call([git_unpack, self.path, path_slow], env={'SLOW_REWRITE': '1'})
        subprocess.call([git_unpack, self.path, path_fast], env={'SLOW_REWRITE': ''})
        repo_slow = git.Repository(path_slow)
        repo_fast = git.Repository(path_fast)
        self.check_same(repo_fast, repo_slow)

    def test_dir2mod_crossref(self):
        git_dir2mod = os.path.join(os.path.dirname(__file__), 'git-dir2mod')
        path_slow = tempfile.mkdtemp(prefix='git-dir2mod-')
        path_fast = tempfile.mkdtemp(prefix='git-dir2mod-')
        print("Slow:", path_slow)
        print("Fast:", path_fast)
        subdir = 'nested/subdir'
        subprocess.call([
            git_dir2mod, self.path, subdir,
            'https://submodule.com',
            path_slow+'.par',
            path_slow+'.sub',
        ], env={'SLOW_REWRITE': '1'})
        subprocess.call([
            git_dir2mod, self.path, subdir,
            'https://submodule.com',
            path_fast+'.par',
            path_fast+'.sub',
        ], env={'SLOW_REWRITE': ''})
        repo_slow = git.Repository(path_slow+'.par')
        repo_fast = git.Repository(path_fast+'.par')
        self.check_same(repo_fast, repo_slow)
        shutil.rmtree(path_slow)
        shutil.rmtree(path_fast)


if __name__ == '__main__':
    unittest.main()
