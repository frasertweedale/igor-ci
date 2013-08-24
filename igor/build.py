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

import os
import subprocess
import time

import pygit2

from . import build_source
from . import build_report
from . import git


class SpecError(Exception):
    """Base class for spec errors."""


class BuildStep:
    """A single step in a build process."""
    @classmethod
    def from_blob(cls, repo, oid):
        """Instantiate from a blob in the given repository."""
        return cls(script=repo[oid].data)

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._script == other._script

    def __ne__(self, other):
        return not self == other

    def __init__(self, *, script):
        self._script = script  # shell script to execute (bytes)

    def execute(self, *, env, cwd):
        """Execute this build step, returning a ``BuildStepReport``.

        ``env``
          Environment in which to execute the build step.
        ``cwd``
          Directory in which to execute the build step.

        """
        t_start = time.time()
        proc = subprocess.Popen(
            ['/bin/sh'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=cwd
        )
        stdout, stderr = proc.communicate(self._script)
        t_finish = time.time()

        return build_report.BuildStepReport(
            t_start=t_start,
            t_finish=t_finish,
            exit=proc.returncode,
            stdout=stdout,
            stderr=stderr
        )


class BuildSpec:
    """A build specification."""
    __slots__ = 'env', 'oid',  'name', 'steps', 'artifacts'
    __attrs__ = __slots__

    @classmethod
    def from_ref(cls, repo, name):
        obj = repo.revparse_single(name)
        return cls.from_commit(repo, name, git.peel(repo, 'commit', obj))

    @classmethod
    def from_commit(cls, repo, name, commit):
        return cls.from_tree(repo, name, commit.oid, commit.tree)

    @classmethod
    def from_tree(cls, repo, name, commit_oid, tree):
        env = None
        if 'env' in tree:
            raise NotImplementedError

        steps = {
            te.name: BuildStep.from_blob(repo, te.oid)
            for te in repo[tree['steps'].oid]
        }

        artifacts = None
        if 'artifacts' in tree:
            raise NotImplementedError

        return cls(
            name=name,
            oid=commit_oid,
            env=env,
            steps=steps,
            artifacts=artifacts
        )

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return all(
                getattr(self, attr) == getattr(other, attr)
                for attr in self.__attrs__
            )
        else:
            return False

    def __repr__(self):
        return '{}({})'.format(
            type(self).__name__,
            ', '.join(
                '{}={}'.format(attr, getattr(self, attr))
                for attr in self.__attrs__
            )
        )

    def __init__(self, *, name, oid, env, steps, artifacts):
        """Initialise the build spec.

        ``name``
          The name of the build spec.
        ``oid``
          The OID of the commit wherein is contained this build spec.
        ``env``
          The value given is a partial environment; the execution
          environment will be the result of merging the given
          ``dict`` into the current environment.  If the given value
          is false, the environment will be unchanged.
          environment
        ``steps``
          Mapping of name to ``BuildStep``.  Build steps will be
          executed in lexicographic order.
        ``artifacts``
          Mapping of paths (relative to root of source checkout)
          keyed by name (to archive as) to be archived, if present
          in the checkout after successful execution of the spec.

        """
        self.name = name
        self.oid = oid
        self.artifacts = artifacts or []
        self.steps = steps
        self.env = env or {}

    def execute(self, *, order, source_oid=None, cwd):
        """Execute the build specification and return a ``BuildReport``.

        If ``order`` is not an assigned and incomplete
        ``BuildOrder``, raise ``SpecError``.

        """
        if not order.assigned or order.completed:
            raise SpecError('order must be assigned and incomplete')

        env = dict(os.environ, **self.env)

        # run the build steps
        step_reports = {}
        for name in sorted(self.steps):
            step_reports[name] = \
                self.steps[name].execute(env=env, cwd=cwd)
            if not step_reports[name].ok():
                break

        # return report
        return build_report.BuildReport(
            spec_oid=self.oid,
            source_oid=source_oid,
            name=self.name,
            order=order.complete(),
            env=env,
            step_reports=step_reports
            # TODO artifacts
        )
