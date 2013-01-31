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

import time
import unittest
import unittest.mock
import uuid

from . import order


class OrderTestCase(unittest.TestCase):
    def setUp(self):
        self.order = order.Order(
            spec_uri='/fake/local/dir',
            spec_ref='build0',
            desc='test',
            source_uri='git://example.org/foo/bar',
            source_args=['abcdef0']
        )

    def test_init_source_args_when_None_gives_empty_tuple(self):
        o = order.Order(
            spec_uri='/fake/local/dir', spec_ref='build0', desc='test',
            source_uri='git://example.org/foo/bar', source_args=None
        )
        self.assertEqual(o.source_args, ())

    def test_obj_is_immutable(self):
        for attr in self.order.__attrs__:
            with self.assertRaises(AttributeError):
                setattr(self.order, attr, 'foo')

    def test_eq_true_for_order_eq_itself(self):
        self.assertTrue(self.order == self.order)

    def test_ne_false_for_order_eq_itself(self):
        self.assertFalse(order != order)

    def test_eq_true_for_different_but_equivalent_orders(self):
        o1 = order.Order(
            id='1234', spec_uri='/fake/dir', spec_ref='build0', desc='test',
            source_uri='git://example.org/foo/bar', source_args=['abcdef0']
        )
        o2 = order.Order(
            id='1234', spec_uri='/fake/dir', spec_ref='build0', desc='test',
            source_uri='git://example.org/foo/bar', source_args=['abcdef0']
        )
        self.assertTrue(o1 == o2)

    def test_ne_false_for_different_but_equivalent_orders(self):
        o1 = order.Order(
            id='1234', desc='test', spec_uri='/fake/dir', spec_ref='build0',
            source_uri='git://example.org/foo/bar', source_args=['abcdef0']
        )
        o2 = order.Order(
            id='1234', desc='test', spec_uri='/fake/dir', spec_ref='build0',
            source_uri='git://example.org/foo/bar', source_args=['abcdef0']
        )
        self.assertFalse(o1 != o2)

    def test_eq_false_for_differing_orders(self):
        self.assertFalse(self.order == self.order.assign('bob'))

    def test_ne_true_for_differing_orders(self):
        self.assertTrue(self.order != self.order.assign('bob'))

    def test_hashable(self):
        self.assertIsInstance(hash(self.order), int)

    def test_hash_same_for_eqivalent_orders(self):
        o1 = order.Order(
            id='1234', spec_uri='/fake/dir', spec_ref='build0', desc='test',
            source_uri='git://example.org/foo/bar', source_args=['abcdef0']
        )
        o2 = order.Order(
            id='1234', spec_uri='/fake/dir', spec_ref='build0', desc='test',
            source_uri='git://example.org/foo/bar', source_args=['abcdef0']
        )
        self.assertEqual(hash(o1), hash(o2))

    def test_hash_different_for_different_orders(self):
        self.assertNotEqual(hash(self.order), hash(self.order.assign('bob')))

    def test_serialises_and_deserialises_into_same_order(self):
        obj = self.order.to_obj()
        o = order.Order.from_obj(obj)
        self.assertEqual(self.order, o)

    def test_auto_uuid_when_no_uuid_given(self):
        uu = uuid.uuid4()
        with unittest.mock.patch('uuid.uuid4', new=lambda: uu):
            o = order.Order(
                spec_uri='/fake/local/dir',
                spec_ref='build0',
                desc='test',
                source_uri='git://example.org/foo/bar',
                source_args=['abcdef0']
            )
            self.assertEqual(o.id, str(uu))

    def test_order_created_unassigned_and_incomplete(self):
        self.assertIsNotNone(self.order.created)
        self.assertIsNone(self.order.assigned)
        self.assertIsNone(self.order.worker)
        self.assertIsNone(self.order.completed)

    def test_assign_sets_assigned_and_worker(self):
        o = self.order.assign('bob')
        self.assertIsNotNone(o.created)
        self.assertIsNotNone(o.assigned)
        self.assertEqual(o.worker, 'bob')
        self.assertIsNone(o.completed)

    def test_assign_when_already_assigned_raises_exception(self):
        with self.assertRaises(order.OrderError):
            self.order.assign('bob').assign('bob')

    def test_unassign_resets_assigned_and_worker(self):
        o = self.order.assign('bob').unassign()
        self.assertIsNotNone(o.created)
        self.assertIsNone(o.assigned)
        self.assertIsNone(o.worker)
        self.assertIsNone(o.completed)

    def test_unassign_returns_order_eq_to_original_order(self):
        o = self.order.assign('bob').unassign()
        self.assertEqual(self.order, o)

    def test_unassign_when_not_assigned_raises_exception(self):
        with self.assertRaises(order.OrderError):
            self.order.unassign()

    def test_unassign_when_complete_raises_exception(self):
        with self.assertRaises(order.OrderError):
            self.order.assign('bob').complete().unassign()

    def test_complete_sets_completed(self):
        o = self.order.assign('bob').complete()
        self.assertIsNotNone(o.created)
        self.assertIsNotNone(o.assigned)
        self.assertEqual(o.worker, 'bob')
        self.assertIsNotNone(o.completed)

    def test_complete_when_not_aassigned_raises_exception(self):
        with self.assertRaises(order.OrderError):
            self.order.complete()

    def test_complete_when_complete_is_idempotent(self):
        o = self.order.assign('bob').complete()
        self.assertEqual(o, o.complete())

    def test_times_are_local_rfc2822(self):
        t = time.localtime()
        t_string = time.strftime("%a, %d %b %Y %H:%M:%S %z", t)
        with unittest.mock.patch('time.localtime', new=lambda: t):
            o = order.Order(
                spec_uri='/fake/local/dir',
                spec_ref='build0',
                desc='test',
                source_uri='git://example.org/foo/bar',
                source_args=['abcdef0']
            ).assign('bob').complete()
            self.assertEqual(o.created, t_string)
            self.assertEqual(o.assigned, t_string)
            self.assertEqual(o.completed, t_string)

    # TODO tests to write/read repo
