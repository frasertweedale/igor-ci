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


class OrderManager:
    def __init__(self):
        self.on_assign = None

        self.orders = {}
        self.subscribers = {}

        self.orderq = collections.deque()
        self.subq = collections.deque()

    def __iter__(self):
        return iter(self.orders.values())

    def subscribe(self, subscriber):
        self.subscribers[subscriber.id] = subscriber
        self.subq.append(subscriber.id)
        self._assign()

    def unsubscribe(self, subscriber):
        """Remove entire subscription for given subscriber."""
        self.subscribers.pop(subscriber.id, None)
        while subscriber.id in self.subq:
            self.subq.remove(subscriber.id)

    def add_order(self, order):
        # TODO check unassigned
        # TODO same order -> do nothing
        self.orders[order.id] = order
        self.orderq.append(order.id)
        self._assign()

    def _assign(self):
        while self.orderq and self.subq:
            order = self.orders[self.orderq.popleft()]
            sub = self.subscribers[self.subq.popleft()]
            order = order.assign(sub.id)
            sub.push_order(order)
            self.orders[order.id] = order
            if self.on_assign is not None:
                self.on_assign(order)
            # remove subscriber if subscription exhausted
            if sub.id not in self.subq:
                del self.subscribers[sub.id]

    def cancel_order(self, order):
        """Return the order or None if it was unknown."""
        while order.id in self.orderq:
            self.orderq.remove(order.id)
        return self.orders.pop(order.id, None)

    def complete_order(self, order):
        return self.complete_order_id(order.id)

    def complete_order_id(self, order_id):
        # TODO only the assigned handler can complete the order
        order = self.orders[order_id]
        order = order.complete()
        del self.orders[order_id]
        return order

    def unassign_order(self, order):
        if order.id in self.orders and self.orders[order.id].assigned:
            self.orders[order.id] = self.orders[order.id].unassign()
            self.orderq.appendleft(order.id)
            self._assign()


class EventManager:
    def __init__(self):
        self.subscribers = {}

    def add(self, subscriber, events):
        self.subscribers[subscriber] = events

    def discard(self, subscriber):
        if subscriber in self.subscribers:
            del self.subscribers[subscriber]

    def __iter__(self):
        return iter(self.subscribers.copy().items())

    def push_event(self, event):
        """Put an event to each subscriber that is subscribed to it."""
        for subscriber, events in self:
            if len(events) == 0 or isinstance(event, events):
                subscriber.push_event(event)
