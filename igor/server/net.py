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

import asyncore
import asynchat
import json
import logging
import uuid

from . import error
from . import event
from . import command

logger = logging.getLogger(__name__)


class Server(asyncore.dispatcher):
    def __init__(self, *, ordermgr, eventmgr):
        self._ordermgr = ordermgr
        self._eventmgr = eventmgr

        super().__init__()
        self.create_socket()
        self.set_reuse_addr()
        self.bind(('', 1602))
        self.listen(5)

    def handle_accepted(self, sock, addr):
        ServerHandler(sock, ordermgr=self._ordermgr, eventmgr=self._eventmgr)


class ServerHandler(asynchat.async_chat):
    def __init__(self, sock, *, ordermgr, eventmgr):
        self.id = str(uuid.uuid4())
        self.ordermgr = ordermgr
        self.eventmgr = eventmgr

        self.ordermgr.on_assign = self.ordermgr_on_assign_cb

        self.ibuf = []
        self.set_terminator(b'\v')
        super().__init__(sock)

    def handle_close(self):
        super().handle_close()
        self.ordermgr.unsubscribe(self)
        self.eventmgr.discard(self)

    def ordermgr_on_assign_cb(self, order):
        self.eventmgr.push_event(event.OrderAssigned(order_id=order.id))

    def push_obj(self, obj):
        """Serialise the object as UTF-8 encoded JSON and send."""
        self.push(json.dumps(obj).encode('UTF-8') + b'\n\v')

    def push_event(self, event):
        self.push_obj(event.to_obj())

    def push_order(self, order):
        self.push_obj({"order": order.to_obj()})

    def collect_incoming_data(self, data):
        self.ibuf.append(data)

    def found_terminator(self):
        data = b''.join(self.ibuf)
        self.ibuf = []
        obj = None
        try:
            self.process_data(data)
        except error.Error as e:
            self.push_obj(e.to_obj())
        except Exception as e:
            logger.exception('unhandled exception')
            exc = error.UnhandledServerError(str(e))
            self.push_obj(exc.to_obj())

    def process_data(self, data):
        obj = None
        try:
            obj = json.loads(data.decode('UTF-8'))
        except Exception as e:
            raise error.ClientError(str(e)) from e
        self.process_obj(obj)

    def process_obj(self, obj):
        if not isinstance(obj, dict) or 'command' not in obj:
            raise error.ClientError('No command given.')
        cmd_cls = None
        try:
            cmd_cls = command.Command.lookup(obj['command'])
        except TypeError:
            raise error.ClientError('Invalid command name.')
        except KeyError:
            raise error.ClientError('No such command.')

        params = obj.get('params', {})
        try:
            params = cmd_cls.parse_params(**params)
        except TypeError as e:
            raise error.ParamError(str(e))

        cmd = cmd_cls(self)
        cmd.execute(**params)
