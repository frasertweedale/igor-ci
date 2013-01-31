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

import abc
import collections
import subprocess

import pygit2


class BuildSource(metaclass=abc.ABCMeta):
    """Base class for mechanism to fetch things to build."""

    impls = collections.OrderedDict()

    @classmethod
    def register(cls, name, impl):
        """Register a build source implementation.

        First to register a given name wins.

        """
        if name in cls.impls:
            raise KeyError('{!r} build source already registered'.format(name))
        cls.impls[name] = impl

    @classmethod
    @abc.abstractmethod
    def handles_uri(cls, uri):
        """Declare whether this source will handle the given URI.

        Return True if it definitely can; False if it definitely
        cannot and None to make no declaration.

        """
        return None

    @classmethod
    def get(cls, name, uri, *args, **kwargs):
        """Instantiate the named implementation."""
        return cls.impls[name](uri, *args, **kwargs)

    @classmethod
    def get_for_uri(cls, uri, *args, **kwargs):
        """Find a registered source that will handle the given URI.

        Implementations are tried in the order that they were
        registered.  The first to return a true value is
        instantiated and returned.  If none of the registered
        implementations return true, raise ``RuntimeError``.

        """
        for impl in cls.impls.values():
            if impl.handles_uri(uri):
                return impl(uri, *args, **kwargs)
        raise RuntimeError('No source available for {!r}.'.format(uri))

    @abc.abstractmethod
    def checkout(self, dest):
        """Checkout the source into the given ``dest`` folder.

        Subclasses should not invoke this method via ``super`` as it
        raises ``NotImplementedError``.

        Return a Git oid for the checked-out revision, or None if
        this does not make sense.  Unless the class specifically
        deals with Git repositories, returning an oid probably does
        not make sense.

        """
        raise NotImplementedError


class GitBuildSource(BuildSource):
    """A Git build source."""

    def __init__(self, url, *args):
        """Initialise the build source.

        ``url``
          A Git URL (i.e. something that can be cloned; see
          git-clone(1).
        ``args[0]``
          A Git tree-ish (i.e. something that can be checked out;
          see git-checkout(1).  Optional; if not given, the
          repository is left at its initial state (i.e., the
          remote's HEAD will be checked out, often "master").

        """
        self._url = url
        self._rev = args[0] if args else None

    @classmethod
    def handles_uri(cls, uri):
        """Determine whether we can handle the given URI using.

        ``git ls-remote`` is invoked to see whether a Git repo lives
        at the given location.

        """
        try:
            subprocess.check_call(
                ['git', 'ls-remote', uri],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError:
            return False
        return True

    def checkout(self, dest):
        """Clone the repository to the given destination.

        Return the oid of the checked-out commit.

        """
        # TODO use pygit2 clone functionality when implemented
        subprocess.check_call(
            ['git', 'clone', '--quiet', self._url, dest],
            stderr=subprocess.DEVNULL
        )
        if self._rev:
            subprocess.check_call(
                ['git', 'checkout', '--quiet', self._rev],
                cwd=dest
            )

        return pygit2.Repository(dest).head.oid

BuildSource.register('git', GitBuildSource)
