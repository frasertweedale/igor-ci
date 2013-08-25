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

import tempfile
import unittest

from . import git
from . import test


class RepositoryTestCase(test.EmptyRepoTestCase):
    def test_signature_no_timestamp_does_not_give_epoch(self):
        sig = git.Repository.signature(time=-1)
        self.assertNotEqual(sig.time, 0)

    def test_signature_default_offset_equals_zero(self):
        sig = git.Repository.signature(time=0)
        self.assertEqual(sig.offset, 0)

    def test_signature_handles_utf8(self):
        sig = git.Repository.signature(name='B\u00f6b')
        self.assertEqual(sig.name, 'B\u00f6b')

    def test_null_report_writes_sensible_commit(self):
        """Null report commit info matches expectations."""
        sig = self.repo.signature(time=0)
        oid = self.repo.null_report()
        commit = self.repo[oid]
        for attr in ['name', 'email', 'time', 'offset']:
            self.assertEqual(
                getattr(commit.author, attr),
                getattr(sig, attr)
            )
            self.assertEqual(
                getattr(commit.committer, attr),
                getattr(sig, attr)
            )
        self.assertEqual(commit.message.strip(), '[NULL] null build report')
        self.assertEqual(commit.parents, [])
        self.assertEqual(
            self.repo[oid].tree.hex,
            '4b825dc642cb6eb9a060e54bf8d69288fbee4904'
        )

    def test_null_report_is_idempotent(self):
        """Null report creation is idempotent."""
        oid_1 = self.repo.null_report()
        oid_2 = self.repo.null_report()
        self.assertEqual(oid_1, oid_2)

    def test_clone_successfully_clones_local_path(self):
        oid = self.repo.null_report()
        self.repo.create_reference('refs/ci/report/foo', oid)
        with tempfile.TemporaryDirectory() as name:
            newrepo = git.Repository.clone(self.repo.path, name)
            newrepo.fetch()
            self.assertIn(oid, newrepo)

    def test_clone_successfully_clones_remote_uri(self):
        oid = self.repo.null_report()
        self.repo.create_reference('refs/ci/report/foo', oid)
        with tempfile.TemporaryDirectory() as name:
            newrepo = git.Repository.clone('file://' + self.repo.path, name)
            newrepo.fetch()
            self.assertIn(oid, newrepo)

    def test_fetch_fetches_new_objects_and_updates_refs(self):
        oid = self.repo.null_report()
        self.repo.create_reference('refs/ci/report/foo', oid)
        with tempfile.TemporaryDirectory() as name:
            newrepo = git.Repository.clone(self.repo.path, name)
            newoid = self.repo.create_commit(
                'refs/ci/report/foo',
                'a later commit',
                self.repo[oid].tree.oid,
                [oid]
            )
            self.assertNotIn(newoid, newrepo)
            newrepo.fetch()
            self.assertIn(newoid, newrepo)
            self.assertEqual(
                newrepo.revparse_single('refs/ci/report/foo').oid,
                newoid
            )

    def test_fetch_fetches_ci_spec_and_ci_report_refs(self):
        oid = self.repo.null_report()
        self.repo.create_reference('refs/ci/spec/foo', oid)
        self.repo.create_reference('refs/ci/report/foo', oid)
        with tempfile.TemporaryDirectory() as name:
            newrepo = git.Repository.clone(self.repo.path, name)
            newrepo.fetch()
            self.assertEqual(
                newrepo.revparse_single('refs/ci/spec/foo').oid,
                oid
            )
            self.assertEqual(
                newrepo.revparse_single('refs/ci/report/foo').oid,
                oid
            )

    def test_clone_or_open_clones_missing_repo(self):
        oid = self.repo.null_report()
        self.repo.create_reference('refs/ci/report/foo', oid)
        with tempfile.TemporaryDirectory() as name:
            newrepo = git.Repository.clone_or_open(self.repo.path, name)
            self.assertIn(oid, newrepo)

    def test_clone_or_open_opens_existing_repo(self):
        oid = self.repo.null_report()
        self.repo.create_reference('refs/ci/report/null', oid)
        with tempfile.TemporaryDirectory() as name:
            newrepo = git.Repository.clone(self.repo.path, name)
            newrepo2 = git.Repository.clone_or_open('ignored', name)
            self.assertIn(oid, newrepo2)
            self.assertEqual(
                newrepo2.revparse_single('refs/ci/report/null').oid,
                oid
            )

    def test_push_in_cloned_repo_returns_True_on_successful_push(self):
        oid = self.repo.null_report()
        self.repo.create_reference('refs/ci/report/foo', oid)
        with tempfile.TemporaryDirectory() as name:
            newrepo = git.Repository.clone(self.repo.path, name)
            newrepo.fetch()
            newoid = newrepo.create_commit(
                'refs/ci/report/foo',
                'a later commit',
                self.repo[oid].tree.oid,
                [oid]
            )
            self.assertNotIn(newoid, self.repo)
            self.assertTrue(newrepo.push('refs/ci/report/foo'))
            self.assertIn(newoid, self.repo)
            self.assertEqual(
                self.repo.revparse_single('refs/ci/report/foo').oid,
                newrepo[newoid].oid
            )

    def test_push_in_cloned_repo_returns_False_on_failed_push(self):
        oid = self.repo.null_report()
        self.repo.create_reference('refs/ci/report/foo', oid)
        with tempfile.TemporaryDirectory() as name:
            newrepo = git.Repository.clone(self.repo.path, name)
            newrepo.fetch()
            newoid1 = self.repo.create_commit(
                'refs/ci/report/foo',
                'a later commit',
                self.repo[oid].tree.oid,
                [oid]
            )
            newoid2 = newrepo.create_commit(
                'refs/ci/report/foo',
                'some other later commit',
                self.repo[oid].tree.oid,
                [oid]
            )
            self.assertFalse(newrepo.push('refs/ci/report/foo'))
            self.assertNotIn(newoid1, newrepo)
            self.assertNotIn(newoid2, self.repo)

    def test_push_with_refspec_pushes_according_to_refspec(self):
        oid = self.repo.null_report()
        self.repo.create_reference('refs/heads/master', oid)
        with tempfile.TemporaryDirectory() as name:
            newrepo = git.Repository.clone(self.repo.path, name)
            newoid = newrepo.create_commit(
                'refs/heads/develop',
                'a commit on branch "develop"',
                self.repo[oid].tree.oid,
                [oid]
            )
            self.assertTrue(newrepo.push('refs/heads/develop'))
            self.assertEqual(
                self.repo.revparse_single('refs/heads/master').oid,
                oid
            )
            self.assertEqual(
                self.repo.revparse_single('refs/heads/develop').oid,
                newrepo[newoid].oid
            )


class RefUtilTestCase(unittest.TestCase):
    def test_split_ref(self):
        self.assertEqual(
            git.split_ref('refs/heads/master'),
            ['refs', 'heads', 'master']
        )

    def test_tail_ref(self):
        self.assertEqual(git.tail_ref('refs/heads/master'), 'master')


class ObjToBytesTestCase(unittest.TestCase):
    def test_result_is_bytes(self):
        self.assertIsInstance(git.obj_to_bytes(''), bytes)

    def test_result_represents_object(self):
        obj = {'a': 1, 'b': 2}
        b = git.obj_to_bytes(obj)
        self.assertEqual(git.bytes_to_obj(b), obj)

    def test_result_has_no_extraneous_whitespace(self):
        b = git.obj_to_bytes({'a': 1, 'b': 2})
        self.assertNotRegex(b' \n', b)
        self.assertNotRegex(b'\n$', b)


class BytesToObjTestCase(unittest.TestCase):
    def test_result_produces_equivalent_bytes(self):
        b1 = git.obj_to_bytes({'a': 1, 'b': 2})
        obj1 = git.bytes_to_obj(b1)
        b2 = git.obj_to_bytes(obj1)
        obj2 = git.bytes_to_obj(b2)
        self.assertEqual(obj1, obj2)
