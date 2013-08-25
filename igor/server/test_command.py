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
import uuid

from .. import order
from . import command
from . import error
from . import event


class CommandTestCase(unittest.TestCase):
    def test_name_returns_class_name(self):
        self.assertEqual(command.Command.name(), "Command")

    def test_inherited_name_method_returns_subclass_name(self):
        class Foo(command.Command):
            def parse_params():
                pass

            def execute():
                pass

        self.assertEqual(Foo.name(), "Foo")

    @unittest.mock.patch(command.__package__ + '.command.Command.commands', {})
    def test_register_returns_registered_command(self):
        class X(command.Command):
            def parse_params():
                pass

            def execute():
                pass

        self.assertIs(command.Command.register(X), X)

    @unittest.mock.patch(command.__package__ + '.command.Command.commands', {})
    def test_register_registers_command_by_name_given_by_name_method(self):
        @command.Command.register
        class Foo(command.Command):
            def parse_params():
                pass

            def execute():
                pass

            @classmethod
            def name(cls):
                return 'FooBar'

        self.assertIs(command.Command.lookup('FooBar'), Foo)

    @unittest.mock.patch(command.__package__ + '.command.Command.commands', {})
    def test_lookup_raises_key_error_on_missing_command(self):
        with self.assertRaises(KeyError):
            command.Command.lookup('bogo')

    @unittest.mock.patch(command.__package__ + '.command.Command.commands', {})
    def test_lookup_finds_command_by_exact_name(self):
        @command.Command.register
        class X(command.Command):
            def parse_params():
                pass

            def execute():
                pass

            @classmethod
            def name(cls):
                return 'FooBar'

        self.assertIs(command.Command.lookup('FooBar'), X)

    @unittest.mock.patch(command.__package__ + '.command.Command.commands', {})
    def test_lookup_finds_command_case_insensitively(self):
        @command.Command.register
        class FooBar(command.Command):
            def parse_params():
                pass

            def execute():
                pass

        self.assertIs(command.Command.lookup('foobar'), FooBar)
        self.assertIs(command.Command.lookup('FOOBAR'), FooBar)
        self.assertIs(command.Command.lookup('fOoBaR'), FooBar)

    @unittest.mock.patch(command.__package__ + '.command.Command.commands', {})
    def test_lookup_strs_argument(self):
        @command.Command.register
        class X(command.Command):
            def parse_params():
                pass

            def execute():
                pass

            @classmethod
            def name(cls):
                return '1'

        self.assertIs(command.Command.lookup(1), X)


class SubscribeTestCase(unittest.TestCase):
    def test_param_events_given_list_returns_tuple(self):
        inargs = {"events": []}
        outargs = command.Subscribe.parse_params(**inargs)
        self.assertIn("events", outargs)
        self.assertIsInstance(outargs['events'], tuple)

    def test_param_events_unknown_event_raises_param_error(self):
        inargs = {"events": ['fakeevent']}
        with self.assertRaises(error.ParamError):
            command.Subscribe.parse_params(**inargs)

    @unittest.mock.patch(event.__package__ + '.event.Event.events', {})
    def test_param_events_known_event_name_replaced_with_type(self):
        @event.Event.register
        class FakeEvent(event.Event):
            pass

        inargs = {"events": ['fakeevent']}
        outargs = command.Subscribe.parse_params(**inargs)
        self.assertIn(FakeEvent, outargs['events'])


class OrderCreateTestCase(unittest.TestCase):
    def test_execute_calls_add_order_on_order_manager(self):
        o = order.Order(
            spec_uri='/fake/local/dir', spec_ref='build0', desc='test',
            source_uri='git://example.org/foo/bar', source_args=['abcdef0']
        )
        h = unittest.mock.Mock()
        cmd = command.OrderCreate(h)
        cmd.execute(**cmd.parse_params(order=o.to_obj()))
        h.ordermgr.add_order.assert_called_once_with(o)


class OrderAssignTestCase(unittest.TestCase):
    def test_execute_calls_subscribe_on_order_manager(self):
        h = unittest.mock.Mock()
        cmd = command.OrderAssign(h)
        cmd.execute(**cmd.parse_params())
        h.ordermgr.subscribe.assert_called_once_with(h)


class OrderCompleteTestCase(unittest.TestCase):
    def test_parse_params_requires_uuid_order_id_and_result(self):
        with self.assertRaises(TypeError):
            command.OrderComplete.parse_params()
        with self.assertRaises(TypeError):
            command.OrderComplete.parse_params(foo=1)
        u = str(uuid.uuid4())
        with self.assertRaises(TypeError):
            command.OrderComplete.parse_params(order_id=u, foo=1)
        with self.assertRaises(TypeError):
            command.OrderComplete.parse_params(foo=1, result='C')

        u = str(uuid.uuid4())[:-1]
        with self.assertRaises(error.ParamError):
            command.OrderComplete.parse_params(order_id=u, result='C')

        u = str(uuid.uuid4())
        weird_u = u.replace('-', '').upper()
        self.assertEqual(
            command.OrderComplete.parse_params(order_id=weird_u, result='C'),
            {'order_id': u, 'result': 'C'}
        )

    def test_execute_calls_complete_id_on_order_manager_with_order_id(self):
        h = unittest.mock.Mock()
        u = str(uuid.uuid4())
        cmd = command.OrderComplete(h)
        cmd.execute(**cmd.parse_params(order_id=u, result='C'))
        h.ordermgr.complete_order_id.assert_called_once_with(u)

    def test_execute_emits_OrderCompleted_event(self):
        h = unittest.mock.Mock()
        u = str(uuid.uuid4())
        cmd = command.OrderComplete(h)
        cmd.execute(**cmd.parse_params(order_id=u, result='C'))
        h.eventmgr.push_event.assert_called_once_with(
            event.OrderCompleted(order_id=u, result='C')
        )
