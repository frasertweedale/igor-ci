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

import pygit2

from . import git


class TemporaryRepo:
    """Context manager that creates a temporary empty repository."""
    def __enter__(self):
        self._dir = tempfile.TemporaryDirectory()
        pygit2.init_repository(self._dir.name, True)
        return git.Repository(self._dir.name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._dir.cleanup()


class EmptyRepoTestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self._tr = TemporaryRepo()
        self.repo = self._tr.__enter__()

    def tearDown(self):
        self._tr.__exit__(None, None, None)
        super().tearDown()
