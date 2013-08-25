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

import collections
import unittest
import unittest.mock

from . import event


class EventTestCase(unittest.TestCase):
    def test_has_events_class_attr_that_is_mapping(self):
        self.assertTrue(hasattr(event.Event, 'events'))
        self.assertIsInstance(event.Event.events, collections.Mapping)

    @unittest.mock.patch(event.__package__ + '.event.Event.events', {})
    def test_lookup_raises_key_error_on_missing_event(self):
        with self.assertRaises(KeyError):
            event.Event.lookup('bogo')

    @unittest.mock.patch(event.__package__ + '.event.Event.events', {})
    def test_lookup_finds_event_by_exact_name(self):
        @event.Event.register
        class X(event.Event):
            @classmethod
            def name(cls):
                return 'FooBar'

        self.assertIs(event.Event.lookup('FooBar'), X)

    def test_to_obj_includes_empty_params_when_no_init_kwargs(self):
        ev = event.Event()
        obj = ev.to_obj()
        self.assertIn('params', obj)
        self.assertEqual(obj['params'], {})

    def test_to_obj_includes_init_kwargs_as_params(self):
        ev = event.Event(x=1, y=2, z=3)
        obj = ev.to_obj()
        self.assertIn('params', obj)
        self.assertEqual(obj['params'], dict(x=1, y=2, z=3))

    @unittest.mock.patch(event.__package__ + '.event.Event.events', {})
    def test_event_equality_methods(self):
        """Events with same type and equivalent args compare equal.

        All other combinations compare false.
        """
        class A(event.Event):
            @classmethod
            def name(cls):
                return 'A'

        class B(event.Event):
            @classmethod
            def name(cls):
                return 'B'

        self.assertTrue(A(x=1) == A(x=1))
        self.assertFalse(A(x=1) != A(x=1))
        self.assertFalse(A(x=1) == B(x=1))
        self.assertTrue(A(x=1) != B(x=1))
        self.assertFalse(A(x=1) == A(x=2))
        self.assertTrue(A(x=1) != A(x=2))
