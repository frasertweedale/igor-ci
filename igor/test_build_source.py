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

import pygit2

from . import build_source
from . import test

class GitBuildSourceTestCase(test.EmptyRepoTestCase):
    def setUp(self):
        super().setUp()
        self._oid = self.repo.null_report()
        self._commit = self._oid.hex[:7]
        self.repo.create_reference('refs/heads/master', self._oid)
        self._target_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._target_dir.cleanup()
        super().tearDown()

    def test_local_clone(self):
        bs = build_source.GitBuildSource(self.repo.path, self._commit)
        bs.checkout(self._target_dir.name)
        repo = pygit2.Repository(self._target_dir.name)
        self.assertIn(self._oid, repo)

    def test_nonlocal_clone(self):
        source = 'file://' + self.repo.path
        bs = build_source.GitBuildSource(source, self._commit)
        bs.checkout(self._target_dir.name)
        repo = pygit2.Repository(self._target_dir.name)
        self.assertIn(self._oid, repo)
