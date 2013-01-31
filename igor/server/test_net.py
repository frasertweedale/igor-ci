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

import unittest
import unittest.mock

from . import command
from . import error
from . import net


class ServerHandlerTestCase(unittest.TestCase):
    @unittest.mock.patch('asynchat.async_chat')
    def setUp(self, mock):
        sock = unittest.mock.Mock()
        self.ordermgr = unittest.mock.Mock()
        self.eventmgr = unittest.mock.Mock()
        self.h = net.ServerHandler(
            sock,
            ordermgr=self.ordermgr,
            eventmgr=self.eventmgr
        )

    def test_handler_exposes_ordermgr(self):
        self.assertTrue(hasattr(self.h, 'ordermgr'))
        self.assertIs(self.h.ordermgr, self.ordermgr)

    def test_handler_exposes_eventmgr(self):
        self.assertTrue(hasattr(self.h, 'eventmgr'))
        self.assertIs(self.h.eventmgr, self.eventmgr)

    def test_handle_close_discards_handler_from_eventmgr(self):
        self.h.handle_close()
        self.eventmgr.discard.assert_called_once_with(self.h)

    def test_process_obj_raises_ClientError_if_obj_not_dict_with_command(self):
        with self.assertRaises(error.ClientError):
            self.h.process_obj(None)
        with self.assertRaises(error.ClientError):
            self.h.process_obj(['command'])
        with self.assertRaises(error.ClientError):
            self.h.process_obj({})

    @unittest.mock.patch(command.__package__ + '.command.Command.commands', {})
    def test_process_obj_instantiates_cmd_with_handler(self):
        cmd = unittest.mock.Mock()
        cmd.name.return_value = 'Foo'
        cmd.parse_params.return_value = {}
        command.Command.register(cmd)

        self.h.process_obj({'command': 'foo', 'params': {}})
        cmd.assert_called_once_with(self.h)

    @unittest.mock.patch(command.__package__ + '.command.Command.commands', {})
    def test_process_obj_executes_cmd_with_params_from_parse_params(self):
        cmd = unittest.mock.Mock()
        cmd.name.return_value = 'Foo'
        cmd.parse_params.return_value = {'bar': 1, 'baz': 2}
        command.Command.register(cmd)

        self.h.process_obj({'command': 'foo', 'params': {}})
        cmd().execute.assert_called_once_with(bar=1, baz=2)
