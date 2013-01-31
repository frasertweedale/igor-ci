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

from . import build
from . import build_report
from . import order


class BuildSpecTestCase(unittest.TestCase):
    def setUp(self):
        self.bs = build.BuildSpec(
            name='foo',
            oid=None,
            env={},
            steps=[],
            artifacts=None
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

    def test_empty_env_does_not_return_os_environ(self):
        # does not return os.environ itself
        bs = build.BuildSpec(name='foo', oid=None, env={}, steps=None, artifacts=None)
        self.assertIsNot(bs.env, os.environ)

        bs = build.BuildSpec(name='foo', oid=None, env=None, steps=None, artifacts=None)
        self.assertIsNot(bs.env, os.environ)

    def test_empty_env_copies_current_environ(self):
        bs = build.BuildSpec(name='foo', oid=None, env={}, steps=None, artifacts=None)
        self.assertEqual(bs.env, os.environ, 'existing environment copied')

        bs = build.BuildSpec(name='foo', oid=None, env=None, steps=None, artifacts=None)
        self.assertEqual(bs.env, os.environ, 'existing environment copied')

    def test_nonempty_env_extends_current_environ(self):
        env = {'FOO': 'BAR'}
        expected = os.environ.copy()
        expected.update(env)
        bs = build.BuildSpec(name='foo', oid=None, env=env, steps=None, artifacts=None)
        self.assertEqual(bs.env, expected, 'new envvars added')

        env = {k: 'FOO' for k in os.environ}
        bs = build.BuildSpec(name='foo', oid=None, env=env, steps=None, artifacts=None)
        self.assertEqual(bs.env, env, 'existing envvars overwritten')
