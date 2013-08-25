# This file is part of igor-ci - the ghastly CI system
# Copyright (C) 2013  Fraser Tweedale
#
# igor-ci is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import re
import subprocess  # TODO use native clone and fetch when available

import pygit2


class Repository(pygit2.Repository):
    """Git repository with Igor extensions."""

    @staticmethod
    def signature(
        name='Igor CI',
        email='igor-ci@frase.id.au',
        time=-1,
        offset=0
    ):
        """Return Igor's committer signature."""
        return pygit2.Signature(name, email, time, offset, encoding='UTF-8')

    @classmethod
    def clone(cls, source, dest):
        """Clone the source repository to the destination with CI refspec.

        We init then fetch rather than cloning so that we can munge
        the refspecs to fetch only CI refs.

        """
        repo = pygit2.init_repository(dest, bare=True)
        remote = repo.create_remote('origin', source)
        repo.config.set_multivar(
            'remote.origin.fetch', '',
            '+refs/ci/spec/*:refs/ci/spec/*')
        repo.config.set_multivar(
            'remote.origin.fetch', 'report',
            '+refs/ci/report/*:refs/ci/report/*')
        repo = cls(dest)
        repo.fetch()
        return repo

    def _git(self, *args):
        args = ['git', '--git-dir', self.path] + list(args) + ['--quiet']
        try:
            subprocess.check_call(args, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError as e:
            if e.returncode < 0:
                raise  # abnormal termination
            else:
                return False  # normal failure condition

    @classmethod
    def clone_or_open(cls, source, dest):
        try:
            return cls(dest)
        except KeyError:
            return cls.clone(source, dest)

    def fetch(self):
        self.remotes[0].fetch()  # TODO check for name 'origin'?

    def push(self, refspec):
        """Push the repository.

        Return True if the push succeeded, otherwise False.

        TODO: with current Git, this can segfault if HEAD doesn't
        point anywhere.  Submit a patch to git, but workaround
        in meantime.

        """
        return self._git('push', 'origin', refspec)

    def null_tree(self):
        """Return oid of the empty tree."""
        return self.TreeBuilder().write()

    def null_report(self):
        """Create the null report commit in the given repo and return its SHA.

        No refs are created; it makes little sense to do that anyway
        since the commit object will always be the same, and any ref
        could be moved or deleted.

        Creation of the null-report commit can be deferred until it
        is actually required.

        """
        return self.create_commit(
            None,                           # no update ref
            '[NULL] null build report',     # message
            self.null_tree(),               # empty tree
            [],                             # no parents
            epoch=True
        )

    def create_commit(self, ref, msg, tree, parents, epoch=False):
        """Create a commit.

        If ``epoch`` is true, the time of the commit signature will
        be set to the UNIX epoch.
        """
        time = 0 if epoch else -1
        return super().create_commit(
            ref,
            self.signature(time=time),
            self.signature(time=time),
            msg,
            tree,
            parents
        )

    def revparse_single(self, rev):
        """Parse the given rev with extended "extended SHA" rules.

        The revparse is first tried verbatim.  If unsuccessful, a
        number of igor-specific heuristics are tried.

        Return the referenced object if an object is found,
        otherwise raise KeyError.  'ci/spec/<ref>' is tried before
        'ci/report/<ref>'.

        """
        transforms = [
            lambda x: x,
            lambda x: 'ci/' + x,
            lambda x: 'ci/spec/' + x,
            lambda x: 'ci/report/' + x,
        ]
        for transform in transforms:
            try:
                return super().revparse_single(transform(rev))
            except:
                continue
        raise KeyError('Revision {!r} not found'.format(rev))


class PeelError(Exception):
    pass


_PEEL_MAP = {
    'ref': pygit2.Reference,
    'blob': pygit2.Blob,
    'commit': pygit2.Commit,
    'tag': pygit2.Tag,
    'tree': pygit2.Tree,
}


def peel(repo, target, obj):
    """Peel the object until we get an object of the target type.

    The ``target`` is either a pygit2 reference or object type or
    one of: 'ref', 'tree', 'blob', 'commit' or 'tag'.
    """
    if target in _PEEL_MAP:
        target = _PEEL_MAP[target]
    t = type(obj)
    if t is target:
        return obj
    elif t is pygit2.Reference:
        return peel(repo, target, repo[obj.resolve().oid])
    elif t is pygit2.Commit:
        return peel(repo, target, obj.tree)
    elif t is pygit2.Tag:
        return peel(repo, target, repo[obj.target])
    else:
        raise PeelError("Can't peel {} to {}".format(type(obj), target))


def split_ref(ref):
    """Utility function to split a ref name into components."""
    return ref.split('/')


def tail_ref(ref):
    """Utility function to return the last component of a ref name."""
    return split_ref(ref)[-1]


def obj_to_bytes(d):
    """Utility to turn a object into nicely formatted UTF-8 encoded bytes."""
    return bytes(
        re.sub(' \n', '\n', json.dumps(d, sort_keys=True, indent=2)),
        'UTF-8'
    )


def bytes_to_obj(b):
    """Utility to turn bytes into a object."""
    return json.loads(str(b, 'UTF-8'))
