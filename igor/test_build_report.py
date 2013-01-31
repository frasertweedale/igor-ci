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
import unittest.mock

import pygit2

from . import build
from . import build_report
from . import git
from . import order
from . import test

order = order.Order(
    spec_uri='/fake/local/dir',
    spec_ref='build0',
    desc='test',
    source_uri='git://example.org/foo/bar',
    source_args=['abcdef0']
)

test_tree_map = {
    'exit': 0,
    't_start': 1000.1,
    't_finish': 2000.2,
    'stdout': b"stdout\n",
    'stderr': b"stderr\n",
}

pass_map = test_tree_map.copy()
pass_map['exit'] = 0
pass_bsr = build_report.BuildStepReport(**pass_map)

fail_map = test_tree_map.copy()
fail_map['exit'] = 1
fail_bsr = build_report.BuildStepReport(**fail_map)

# a mock BuildSpec with two steps
mock_spec_2 = unittest.mock.Mock(spec_set=build.BuildSpec)
mock_spec_2.steps = ['one', 'two']


class BuildStepReportTestCase(test.EmptyRepoTestCase):
    def test_object_is_immutable(self):
        bsr = build_report.BuildStepReport(**pass_map)
        for name in bsr.__attrs__:
            with self.assertRaises(AttributeError):
                setattr(bsr, name, 'foo')

    def test_write_then_read_yields_eq_obj(self):
        oid = pass_bsr.write(self.repo)
        self.assertEqual(
            build_report.BuildStepReport.from_tree(self.repo[oid]),
            pass_bsr
        )

    def test_ok_return_true_if_exit_code_is_zero(self):
        self.assertTrue(pass_bsr.ok())

    def test_ok_return_false_if_exit_code_is_nonzero(self):
        self.assertFalse(fail_bsr.ok())


class BuildReportTestCase(test.EmptyRepoTestCase):
    def setUp(self):
        super().setUp()
        self.spec_oid = self.repo.create_commit(
            None, 'bogo spec', self.repo.null_tree(), []
        )
        self.source_oid = self.repo.create_commit(
            None, 'bogo source', self.repo.null_tree(), []
        )

    def test_init_with_incomplete_order_raises_exception(self):
        with self.assertRaises(build_report.ReportError):
            br = build_report.BuildReport(
                name='foo',
                order=order,
                spec_oid=self.spec_oid,
                env={},
                step_reports={'100': pass_bsr, '200': pass_bsr}
            )

        with self.assertRaises(build_report.ReportError):
            br = build_report.BuildReport(
                name='foo',
                order=order.assign('bob'),
                spec_oid=self.spec_oid,
                env={},
                step_reports={'100': pass_bsr, '200': pass_bsr}
            )

    def test_init_with_complete_order_does_not_raise_exception(self):
        br = build_report.BuildReport(
            name='foo',
            order=order.assign('bob').complete(),
            spec_oid=self.spec_oid,
            env={},
            step_reports={'100': pass_bsr, '200': pass_bsr}
        )

    def test_ok_returns_true_with_no_failed_steps(self):
        br = build_report.BuildReport(
            name='foo',
            order=order.assign('bob').complete(),
            spec_oid=self.spec_oid,
            env={},
            step_reports={'100': pass_bsr, '200': pass_bsr}
        )
        self.assertTrue(br.ok())

    def test_ok_returns_false_with_failed_step(self):
        br = build_report.BuildReport(
            name='foo',
            order=order.assign('bob').complete(),
            spec_oid=self.spec_oid,
            env={},
            step_reports={'100': pass_bsr, '200': fail_bsr}
        )

    def test_result(self):
        br = build_report.BuildReport(
            name='foo',
            order=order.assign('bob').complete(),
            spec_oid=self.spec_oid,
            env={},
            step_reports=[]
        )

        # mock the spec
        br._spec = unittest.mock.Mock(spec_set=build.BuildSpec)
        br._spec.steps = ['one', 'two']

        br.step_reports = {'100': pass_bsr, '200': fail_bsr}
        self.assertEqual(br.result(), 'FAIL')

        br.step_reports = {'100': pass_bsr, '200': pass_bsr}
        self.assertEqual(br.result(), 'PASS')

    def test_message_indicates_fail_with_failed_step(self):
        br = build_report.BuildReport(
            name='foo',
            order=order.assign('bob').complete(),
            spec_oid=self.spec_oid,
            env={},
            step_reports={'100': pass_bsr, '200': fail_bsr}
        )
        self.assertEqual(br.message(), '[{}] foo'.format(br.result()))

    def test_message_indicates_success_with_no_failed_steps(self):
        br = build_report.BuildReport(
            name='foo',
            order=order.assign('bob').complete(),
            spec_oid=self.spec_oid,
            env={},
            step_reports={'100': pass_bsr, '200': pass_bsr}
        )
        self.assertEqual(br.message(), '[{}] foo'.format(br.result()))

    def test_in_repo_after_write(self):
        br = build_report.BuildReport(
            name='foo',
            order=order.assign('bob').complete(),
            spec_oid=self.spec_oid,
            env={},
            step_reports={'100': pass_bsr, '200': pass_bsr}
        )
        oid = br.write(self.repo, self.repo.null_report())
        self.assertIn(oid, self.repo)

    def test_write_then_read_yields_eq_obj(self):
        br = build_report.BuildReport(
            name='foo',
            order=order.assign('bob').complete(),
            spec_oid=self.spec_oid,
            env={},
            step_reports={'100': pass_bsr, '200': pass_bsr}
        )
        oid = br.write(self.repo, self.repo.null_report())
        br2 = build_report.BuildReport.from_commit(self.repo[oid])
        for name in (
            'spec_oid', 'source_oid',
            'name', 'order', 'env', 'step_reports',
        ):
            self.assertEqual(getattr(br, name), getattr(br2, name), name)
        self.assertEqual(br, br2)
