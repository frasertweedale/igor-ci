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


class Error(Exception):
    def to_obj(self):
        return {'error': type(self).__name__, 'message': str(self)}


class ServerError(Error):
    """Server exception."""


class UnhandledServerError(ServerError):
    """Unhandled server exception, indicating programmer error."""


class ClientError(Error):
    """General client error."""


class CommandError(ClientError):
    """Client has error in command selection."""

class ParamError(ClientError):
    """Client has error in command parameters."""
