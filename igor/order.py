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

import binascii
import functools
import logging
import operator
import os
import tempfile
import time
import uuid

import pygit2

from . import git

logger = logging.getLogger(__name__)


class OrderError(Exception):
    """Base class for order errors."""


class Order:
    __attrs__ = {
        'id', 'desc', 'spec_uri', 'spec_ref', 'source_uri', 'source_args',
        'env', 'created', 'assigned', 'completed', 'worker',
    }

    @classmethod
    def from_obj(cls, obj):
        keys = obj.keys() & cls.__attrs__  # ignore unrecogised keys
        kwargs = {k: obj[k] for k in keys}
        return cls(**kwargs)

    @classmethod
    def from_blob(cls, blob):
        return cls.from_obj(git.bytes_to_obj(blob.data))

    def to_obj(self):
        return {attr: getattr(self, attr) for attr in self.__attrs__}

    def write(self, repo):
        """Write this order to the given repo and return the blob oid."""
        return repo.create_blob(git.obj_to_bytes(self.to_obj()))

    def __init__(
        self, *,
        id=None, desc, spec_uri, spec_ref, source_uri, source_args,
        env=None, created=None, assigned=None, completed=None, worker=None
    ):
        """Initialise the Order."""
        self.id = id or str(uuid.uuid4())
        self.spec_uri = spec_uri
        self.spec_ref = spec_ref
        self.desc = desc
        self.env = env or ()  # TODO better conversion to/from obj
        self.source_uri = source_uri
        self.source_args = tuple(source_args or ())
        self.created = created or time.strftime("%a, %d %b %Y %H:%M:%S %z")
        self.assigned = assigned
        self.completed = completed
        self.worker = worker

        self.initialised = True

    def __setattr__(self, name, value):
        if hasattr(self, 'initialised'):
            raise AttributeError('immutable object')
        object.__setattr__(self, name, value)

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return all(
                getattr(self, attr) == getattr(other, attr)
                for attr in self.__attrs__
            )
        else:
            return False

    def __hash__(self):
        return functools.reduce(
            operator.xor,
            (hash(getattr(self, attr)) for attr in self.__attrs__)
        )

    def __repr__(self):
        return '{}({})'.format(
            type(self).__name__,
            ', '.join(
                '{}={}'.format(attr, getattr(self, attr))
                for attr in self.__attrs__
            )
        )

    def _mutate(self, **kwargs):
        return type(self)(**dict(self.to_obj(), **kwargs))

    def assign(self, worker):
        """Assign the task to a worker."""
        if self.assigned:
            raise OrderError('cannot assign an already-assigned task')
        return self._mutate(
            assigned=time.strftime("%a, %d %b %Y %H:%M:%S %z"),
            worker=worker
        )

    def unassign(self):
        """Unassign the task, resetting the assigned time and worker."""
        if not self.assigned:
            raise OrderError('cannot unassign an unassigned task')
        if self.completed:
            raise OrderError('cannot unassign a completed task')
        return self._mutate(assigned=None, worker=None)

    def complete(self):
        """Record the order completion time."""
        if not self.assigned:
            raise OrderError('cannot complete an unassigned task')
        return self if self.completed else \
            self._mutate(completed=time.strftime("%a, %d %b %Y %H:%M:%S %z"))

    @staticmethod
    def _prev_oid(repo, report_ref):
        logger.debug('looking for commit: {!r}'.format(report_ref))
        obj = None
        try:
            obj = repo.revparse_single(report_ref)
        except:
            logger.debug('found nothing (no such ref)')
            return None
        if isinstance(obj, pygit2.Commit):
            logger.debug('found commit: {}'.format(binascii.b2a_hex(obj.oid)[:7]))
            return obj.oid
        else:
            logger.warning('found non-commit object')
            return None  # TODO raise an error here?

    def execute(self):
        """Execute the build order and write the report.

        Spec and source contruction are deferred until execution
        because only the executor needs it; intermediaries should
        not care (or have to deal with errors).

        """
        # HACK: avoid circular import
        # TODO: refactor to avoid this situation; perhaps there
        # is a "build executor" domain concept, with strategies
        # for native igor, Travis or other build spec types
        #
        from . import build
        from . import build_source

        repo_path = uri_to_igor_repo_path(self.spec_uri)
        logger.debug('using local spec repo path: {}'.format(repo_path))
        repo = git.Repository.clone_or_open(self.spec_uri, repo_path)
        repo.fetch()
        spec = build.BuildSpec.from_ref(repo, self.spec_ref)

        # shortcut: clone from cache if spec and source are from same repo
        source = build_source.BuildSource.get_for_uri(
            self.source_uri if self.source_uri != self.spec_uri else repo_path,
            *self.source_args
        )
        report_ref = 'refs/ci/report/' + git.tail_ref(self.spec_ref)

        # TODO could we make the BuildSource itself be the ctxt
        # mgr and do both tempdir and checking in its __enter__?
        with tempfile.TemporaryDirectory() as name:
            source_oid = source.checkout(name)
            build_report = spec.execute(
                order=self,
                source_oid=source_oid,
                cwd=name
            )

        # 1. fetch ci refs from origin (overwriting local refs)
        # 2. write the report, succeeding the current report-ref
        # 3. attempt push
        # 4. go to 1 if failed (non-fast-forward) else finish
        #
        pushed = False
        while not pushed:
            repo.fetch()
            prev_oid = self._prev_oid(repo, report_ref) or repo.null_report()
            logger.info('prev_oid: {}'.format(binascii.b2a_hex(prev_oid)[:7]))
            report_commit = build_report.write(repo, prev_oid)
            repo.create_reference(report_ref, report_commit, force=True)
            pushed = repo.push(report_ref)


def uri_to_igor_repo_path(uri):
    """Normalise and transform a repo URI to a local path."""
    if uri.startswith(('/', '.')):
        uri = os.path.abspath(uri)
    return '/tmp/igor{}'.format(hash(uri))
