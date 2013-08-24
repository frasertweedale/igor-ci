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
import time
import unittest
import unittest.mock

import pygit2

from . import build
from . import build_report
from . import order
from . import test


class BuildSpecReadTestCase(test.EmptyRepoTestCase):
    """Test case to read a build spec from a repository."""
    def test_successfully_reads_build_spec_with_multiple_steps(self):
        steps_tb = self.repo.TreeBuilder()
        oid = self.repo.create_blob(b'true')
        steps_tb.insert('1', oid, pygit2.GIT_FILEMODE_BLOB)
        oid = self.repo.create_blob(b'ls')
        steps_tb.insert('2', oid, pygit2.GIT_FILEMODE_BLOB)

        tb = self.repo.TreeBuilder()
        tb.insert('steps', steps_tb.write(), pygit2.GIT_FILEMODE_TREE)

        commit_oid = self.repo.create_commit(
            'refs/ci/spec/test',
            'test spec',
            tb.write(),
            []
        )

        self.assertEqual(
            build.BuildSpec.from_ref(self.repo, 'refs/ci/spec/test'),
            build.BuildSpec(
                name='refs/ci/spec/test',
                oid=commit_oid,
                steps={
                    '1': build.BuildStep(script=b'true'),
                    '2': build.BuildStep(script=b'ls'),
                },
                env=None,
            )
        )


class BuildSpecTestCase(unittest.TestCase):
    def setUp(self):
        self.bs = build.BuildSpec(
            name='foo',
            oid=None,
            env={},
            steps=[],
        )
        self.o = order.Order(
            spec_uri='/tmp/fake/local/dir',
            spec_ref='build0',
            desc='test',
            source_uri='git://example.org/foo/bar',
            source_args=['abcdef0']
        )

    def test_execute_with_unassigned_order_raises_spec_error(self):
        with self.assertRaises(build.SpecError):
            self.bs.execute(order=self.o, source_oid=None, cwd='.')

    def test_execute_with_completed_order_raises_spec_error(self):
        o = self.o.assign('bob').complete()
        with self.assertRaises(build.SpecError):
            self.bs.execute(order=o, source_oid=None, cwd='.')

    def test_execute_inits_build_report_with_completed_order(self):
        o = self.o.assign('bob')
        t = time.localtime()
        with unittest.mock.patch.object(build_report, 'BuildReport') as mock, \
                unittest.mock.patch('time.localtime', new=lambda: t):
            self.bs.execute(order=o, source_oid=None, cwd='.')
            mock.assert_called_once(order=o.complete())
            args, kwargs = mock.call_args
            self.assertIn('order', kwargs)
            self.assertEqual(kwargs['order'], o.complete())

    def test_init_sets_name(self):
        self.assertEqual(self.bs.name, 'foo')

    def test_empty_env_copies_current_environ(self):
        o = self.o.assign('bob')
        expected = dict(os.environ)

        bs = build.BuildSpec(name='foo', oid=None, env=None, steps={})
        with unittest.mock.patch.object(build_report, 'BuildReport') as mock:
            br = bs.execute(order=o, source_oid=None, cwd='.')
        self.assertIsNot(mock.call_args[1]['env'], os.environ)
        self.assertEqual(mock.call_args[1]['env'], expected)

        bs = build.BuildSpec(name='foo', oid=None, env={}, steps={})
        with unittest.mock.patch.object(build_report, 'BuildReport') as mock:
            br = bs.execute(order=o, source_oid=None, cwd='.')
        self.assertIsNot(mock.call_args[1]['env'], os.environ)
        self.assertEqual(mock.call_args[1]['env'], expected)

    def test_nonempty_env_extends_current_environ(self):
        o = self.o.assign('bob')

        env = {'FOO': 'BAR'}
        expected = dict(os.environ, **env)
        bs = build.BuildSpec(name='foo', oid=None, env=env, steps={})
        with unittest.mock.patch.object(build_report, 'BuildReport') as mock:
            br = bs.execute(order=o, source_oid=None, cwd='.')
        self.assertEqual(mock.call_args[1]['env'], expected, 'augments env')

        env = {k: 'FOO' for k in os.environ}
        expected = dict(os.environ, **env)
        bs = build.BuildSpec(name='foo', oid=None, env=env, steps={})
        with unittest.mock.patch.object(build_report, 'BuildReport') as mock:
            br = bs.execute(order=o, source_oid=None, cwd='.')
        self.assertEqual(mock.call_args[1]['env'], expected, 'overrides env')
