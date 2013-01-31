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
from . import event
from . import queue


class OrderManagerTestCase(unittest.TestCase):
    def _order(self):
        return order.Order(
            spec_uri='/fake/local/dir', spec_ref='build0', desc='test',
            source_uri='git://example.org/foo/bar', source_args=['abcdef0']
        )

    def _handler(self):
        m = unittest.mock.Mock()
        m.id = uuid.uuid4()
        return m

    def setUp(self):
        self.om = queue.OrderManager()
        self.o = self._order()

    def test_subscribe_increases_subscription_by_one_order(self):
        m = self._handler()
        self.om.subscribe(m)
        self.om.subscribe(m)
        o1, o2, o3 = self._order(), self._order(), self._order()
        self.om.add_order(o1)
        self.om.add_order(o2)
        self.om.add_order(o3)  # should not be pushed to m
        self.assertEqual(m.push_order.call_count, 2)
        m.push_order.assert_has_calls([
            unittest.mock.call(o1.assign(m.id)),
            unittest.mock.call(o2.assign(m.id))
        ])

    def test_unsubscribe_voids_multiple_subscriptions(self):
        m = self._handler()
        self.om.subscribe(m)
        self.om.subscribe(m)
        self.om.unsubscribe(m)
        self.om.add_order(self.o)
        self.assertFalse(m.push_order.called)

    def test_unsubscribe_when_no_subscriptions_has_no_effect(self):
        m = unittest.mock.Mock()
        self.om.unsubscribe(m)
        self.om.add_order(self.o)
        self.assertFalse(m.push_order.called)

    def test_order_not_in_OM_prior_to_add(self):
        self.assertNotIn(self.o, self.om)

    def test_order_in_OM_after_add(self):
        self.om.add_order(self.o)
        self.assertIn(self.o, self.om)

    def test_order_in_OM_after_assignment(self):
        self.om.add_order(self.o)
        self.om.subscribe(self._handler())
        self.assertNotIn(self.o, self.om)

    def test_order_not_in_OM_after_cancel_prior_to_assignment(self):
        self.om.add_order(self.o)
        self.om.cancel_order(self.o)
        self.assertNotIn(self.o, self.om)

    def test_order_not_in_OM_after_cancel_after_assignment(self):
        self.om.add_order(self.o)
        self.om.subscribe(self._handler())
        self.om.cancel_order(self.o)
        self.assertNotIn(self.o, self.om)

    def test_order_in_OM_after_unassign_prior_to_assignment(self):
        self.om.add_order(self.o)
        self.om.unassign_order(self.o)
        self.assertIn(self.o, self.om)

    def test_order_in_OM_after_unassign_after_assignment(self):
        self.om.add_order(self.o)
        self.om.subscribe(self._handler())
        self.om.unassign_order(self.o)
        self.assertIn(self.o, self.om)

    def test_order_not_in_OM_after_complete_order(self):
        self.om.add_order(self.o)
        self.om.subscribe(self._handler())
        self.om.complete_order(self.o)
        self.assertNotIn(self.o, self.om)

    def test_order_not_in_OM_after_complete_order_id(self):
        self.om.add_order(self.o)
        self.om.subscribe(self._handler())
        self.om.complete_order_id(self.o.id)
        self.assertNotIn(self.o, self.om)

    def test_push_pushes_order_to_one_subscriber_only(self):
        m1, m2 = self._handler(), self._handler()
        self.om.subscribe(m1)
        self.om.subscribe(m2)
        self.om.add_order(self.o)
        if m1.push_order.called:
            m1.push_order.assert_called_once_with(self.o.assign(m1.id))
            self.assertFalse(m2.push_order.called)
        else:
            m2.push_order.assert_called_once_with(self.o.assign(m2.id))
            self.assertFalse(m1.push_order.called)

    def test_push_holds_order_until_subscriber_available(self):
        m = self._handler()
        self.om.add_order(self.o)
        self.om.subscribe(m)
        m.push_order.assert_called_once_with(self.o.assign(m.id))

    def test_cancel_order_returns_none_if_unknown(self):
        self.om.cancel_order(self.o)
        self.assertIsNone(self.om.cancel_order(self.o))

    def test_cancel_order_returns_unassigned_order_if_unassigned(self):
        self.om.add_order(self.o)
        o = self.om.cancel_order(self.o)
        self.assertEqual(o, self.o)

    def test_cancel_order_returns_assigned_order_if_assigned(self):
        self.om.add_order(self.o)
        h = self._handler()
        self.om.subscribe(h)
        o = self.om.cancel_order(self.o)
        self.assertEqual(o, self.o.assign(h.id))

    def test_unassign_unassigned_order_has_no_effect(self):
        h = self._handler()
        self.om.add_order(self.o)
        self.om.unassign_order(self.o)
        self.om.subscribe(h)
        h.push_order.assert_called_once_with(self.o.assign(h.id))

    def test_unassign_assigned_order_reassigns_it_to_next_subscriber(self):
        h1, h2 = self._handler(), self._handler()
        self.om.subscribe(h1)
        self.om.subscribe(h2)
        self.om.add_order(self.o)
        self.om.unassign_order(self.o)
        h2.push_order.assert_called_once_with(self.o.assign(h2.id))

    def test_complete_order_returns_complete_order(self):
        self.om.add_order(self.o)
        h = self._handler()
        self.om.subscribe(h)
        o = self.om.complete_order(self.o)
        self.assertEqual(o, self.o.assign(h.id).complete())

    def test_complete_order_id_returns_complete_order(self):
        self.om.add_order(self.o)
        h = self._handler()
        self.om.subscribe(h)
        o = self.om.complete_order_id(self.o.id)
        self.assertEqual(o, self.o.assign(h.id).complete())

    def test_on_assign_callback_is_called_with_assigned_order(self):
        cb = unittest.mock.Mock()
        self.om.on_assign = cb
        h = self._handler()
        self.om.subscribe(h)
        self.assertFalse(cb.called)
        self.om.add_order(self.o)
        cb.assert_called_once_with(self.o.assign(h.id))


class EventManagerTestCase(unittest.TestCase):
    def setUp(self):
        self.em = queue.EventManager()

    @unittest.mock.patch(event.__package__ + '.event.Event.events', {})
    def test_add_existing_subscriber_updates_subscription(self):
        @event.Event.register
        class Foo(event.Event):
            pass

        @event.Event.register
        class Bar(event.Event):
            pass

        m = unittest.mock.Mock()

        self.em.add(m, (Foo,))
        ev = Foo()
        self.em.push_event(ev)
        m.push_event.assert_called_once_with(ev)

        self.em.add(m, (Bar,))
        self.em.push_event(Foo())
        m.push_event.assert_called_once_with(ev)  # subscription changed

    def test_discard_nonsubscriber_has_no_effect(self):
        @event.Event.register
        class Foo(event.Event):
            pass

        m1, m2 = unittest.mock.Mock(), unittest.mock.Mock()
        self.em.add(m1, ())
        self.em.discard(m2)
        ev = Foo()
        self.em.push_event(ev)
        m1.push_event.assert_called_once_with(ev)
        self.assertFalse(m2.push_event.called)

    @unittest.mock.patch(event.__package__ + '.event.Event.events', {})
    def test_discard_subscriber_unsubscribes_it(self):
        @event.Event.register
        class Foo(event.Event):
            pass

        m = unittest.mock.Mock()
        self.em.add(m, ())
        self.em.discard(m)

        self.em.push_event(Foo())
        self.assertFalse(m.push_event.called, 'did not receive event')

    @unittest.mock.patch(event.__package__ + '.event.Event.events', {})
    def test_push_event_pushes_once_only_to_all_subscribers_only(self):
        @event.Event.register
        class Foo(event.Event):
            pass

        @event.Event.register
        class Bar(event.Event):
            pass

        m1 = unittest.mock.Mock()
        m2 = unittest.mock.Mock()
        m3 = unittest.mock.Mock()
        self.em.add(m1, ())
        self.em.add(m2, (Foo,))
        self.em.add(m3, (Bar,))

        ev = Foo()
        self.em.push_event(ev)

        m1.push_event.assert_called_once_with(ev)
        m2.push_event.assert_called_once_with(ev)
        self.assertFalse(m3.push_event.called)

    def test_iter_iterates_on_copy_of_set(self):
        self.em.add(unittest.mock.Mock(), ())
        self.em.add(unittest.mock.Mock(), ())
        iterator = iter(self.em)
        next(iterator)
        self.em.add(unittest.mock.Mock(), ())
        next(iterator)
        with self.assertRaises(StopIteration, msg="only 2 items in iterator"):
            next(iterator)
        self.assertEqual(len(list(self.em)), 3, "item added during iteration")
