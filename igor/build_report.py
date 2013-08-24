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

import re
import json

import pygit2

from . import order
from . import git


class ReportError(Exception):
    """Base class for report errors."""


class BuildStepReport:
    __attrs__ = {'exit', 't_start', 't_finish', 'stdout', 'stderr'}

    @classmethod
    def from_tree(cls, repo, oid):
        tree = repo[oid]
        return cls(
            exit=int(repo[tree['exit'].oid].data),
            t_start=float(repo[tree['t_start'].oid].data),
            t_finish=float(repo[tree['t_finish'].oid].data),
            stdout=repo[tree['stdout'].oid].data,
            stderr=repo[tree['stderr'].oid].data
        )

    def __init__(self, *, exit, t_start, t_finish, stdout, stderr):
        """Initialise the build step report.

        ``exit``
          Integer exit code of the build step script.
        ``t_start``
          Time that the step started as UTC UNIX timestamp.
        ``t_finish``
          Time that the step finished as UTC UNIX timestamp.
        ``stdout``
          ``bytes`` of standard output.
        ``stderr``
          ``bytes`` of standard error.

        """
        self.exit = exit
        self.t_start = t_start
        self.t_finish = t_finish
        self.stdout = stdout
        self.stderr = stderr
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

    def __repr__(self):
        return '{}({})'.format(
            type(self).__name__,
            ', '.join(
                '{}={}'.format(attr, getattr(self, attr))
                for attr in self.__attrs__
            )
        )

    def ok(self):
        """Return the result of the build step as ``bool``."""
        return self.exit == 0

    def write(self, repo):
        """Write the build step report into the repo and return oid of tree."""
        tb = repo.TreeBuilder()

        oid = repo.create_blob(bytes(str(self.exit) + '\n', 'UTF-8'))
        tb.insert('exit', oid, pygit2.GIT_FILEMODE_BLOB)
        oid = repo.create_blob(bytes(str(self.t_start) + '\n', 'UTF-8'))
        tb.insert('t_start', oid, pygit2.GIT_FILEMODE_BLOB)
        oid = repo.create_blob(bytes(str(self.t_finish) + '\n', 'UTF-8'))
        tb.insert('t_finish', oid, pygit2.GIT_FILEMODE_BLOB)
        oid = repo.create_blob(self.stdout)
        tb.insert('stdout', oid, pygit2.GIT_FILEMODE_BLOB)
        oid = repo.create_blob(self.stderr)
        tb.insert('stderr', oid, pygit2.GIT_FILEMODE_BLOB)

        return tb.write()


class BuildReport:
    @classmethod
    def from_commit(cls, repo, oid):
        commit = repo[oid]
        parents = [c.oid for c in commit.parents]
        step_reports = {
            te.name: BuildStepReport.from_tree(repo, te.oid)
            for te in repo[commit.tree['steps'].oid]
        }
        return cls(
            spec_oid=parents[1],
            source_oid=parents[2] if len(parents) >= 3 else None,
            name=re.search(r'(?<= ).*', commit.message).group(),
            order=order.Order.from_blob(repo[commit.tree['order'].oid]),
            env=git.bytes_to_obj(repo[commit.tree['env'].oid].data),
            step_reports=step_reports
        )

    def __init__(self, *,
        spec_oid,
        source_oid=None,
        name,
        order,
        env,
        step_reports
    ):
        """Initialise the build report.

        ``spec_oid``
          The oid of the BuildSpec from which this BuildReport was
          generated.
        ``source_oid``
          Oid of the source commit which was built, or ``None`` if
          outside the Igor repository.
        ``name``
          The name of the build.  Either ``name`` or ``message``
          must be supplied, but not both.
        ``order``
          A complete build order.  Raise exception if not complete.
        ``env``
          Mapping of the build environment.
        ``step_reports``
          Mapping of ``BuildStepReport`` values.  The order is
          implicit in the keys (i.e., lexicographic order).

        """
        self.spec_oid = spec_oid
        self.source_oid = source_oid

        self.name = name
        if not order.completed:
            raise ReportError('order must be complete')
        self.order = order
        self.env = env
        self.step_reports = step_reports

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return all(
                getattr(self, name) == getattr(other, name)
                for name in (
                    'spec_oid', 'source_oid',
                    'name', 'order', 'env', 'step_reports',
                )
            )
        else:
            return False

    def message(self):
        """Generate the commit message for this build report."""
        return '[{}] {}'.format(self.result(), self.name)

    def ok(self):
        """Return the result of the build.

        This method checks the all steps have passed, but does not
        check that the number of steps is the same as the number
        of steps in the spec.

        """
        return all(x.ok() for x in self.step_reports.values())

    def result(self):
        """Return a textual representation of the result."""
        return 'PASS' if self.ok() else 'FAIL'

    def _write_tree(self, repo):
        """Write tree into the repo and return the object ID."""
        tb = repo.TreeBuilder()

        tb.insert(
            'order',
            self.order.write(repo),
            pygit2.GIT_FILEMODE_BLOB
        )
        blob = repo.create_blob(git.obj_to_bytes(dict(self.env)))
        tb.insert('env', blob, pygit2.GIT_FILEMODE_BLOB)
        blob = repo.create_blob(self.result().encode('UTF-8'))
        tb.insert('result', blob, pygit2.GIT_FILEMODE_BLOB)

        steps_tb = repo.TreeBuilder()
        for name, report in self.step_reports.items():
            steps_tb.insert(name, report.write(repo), pygit2.GIT_FILEMODE_TREE)
        tb.insert('steps', steps_tb.write(), pygit2.GIT_FILEMODE_TREE)
        return tb.write()

    def write(self, repo, prev_oid):
        """Write to the repository and return the commit oid.

        This method does not write or update any refs; this is the
        caller's responsibility.

        """
        parents = [prev_oid, self.spec_oid]
        if self.source_oid and self.source_oid in repo:
            parents.append(self.source_oid)

        return repo.create_commit(
            None, self.message(), self._write_tree(repo), parents
        )
