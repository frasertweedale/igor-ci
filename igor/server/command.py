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
import uuid

from .. import order as _order

from . import error
from . import event


class Command(metaclass=abc.ABCMeta):
    commands = {}

    @classmethod
    def register(cls, command):
        name = command.name().lower()
        if name not in cls.commands:
            cls.commands[name] = command
            return command
        elif cls.commands[name] is not command:
            raise KeyError("Command name {!r} already registered".format(name))

    @classmethod
    def lookup(cls, name):
        return cls.commands[str(name).lower()]

    @classmethod
    def name(cls):
        """Return the name of the command.

        This base implementation returns the name of the class.
        Subclasses for which this does not hold must override this
        class method.

        """
        return cls.__name__

    def __init__(self, handler):
        self.handler = handler

    @classmethod
    @abc.abstractmethod
    def parse_params(cls, **kwargs):
        """Parse params into a ``dict`` or raise ``ParamsError``.

        Keyword arguments from the client will be given.  A
        restrictive method signature is recommended; ``TypeError``
        resulting from incorrect parameters will be caught
        automatically and an error returned to the client.

        """

    @abc.abstractmethod
    def execute(self, **kwargs):
        """Execute the method, returning object to send to client."""


@Command.register
class Subscribe(Command):
    @classmethod
    def parse_params(cls, *, events):
        if not isinstance(events, list):
            raise error.ParamError('events is not a list')
        return {'events': tuple(map(cls._event_cls, events))}

    @staticmethod
    def _event_cls(name):
        try:
            return event.Event.lookup(name)
        except TypeError:
            raise error.ParamError('invalid event name: {}'.format(name))
        except KeyError:
            raise error.ParamError('unknown event: {}'.format(name))

    def execute(self, *, events):
        self.handler.eventmgr.add(self.handler, events)
        self.handler.eventmgr.push_event(event.Subscribe())


@Command.register
class Unsubscribe(Command):
    @classmethod
    def parse_params(cls, **kwargs):
        return {}

    def execute(self):
        self.handler.eventmgr.discard(self.handler)
        self.handler.eventmgr.push_event(event.Unsubscribe())


@Command.register
class OrderCreate(Command):
    @classmethod
    def parse_params(cls, *, order):
        """Instantiate order from JSON."""
        return {'order': _order.Order.from_obj(order)}

    def execute(self, *, order):
        self.handler.ordermgr.add_order(order)
        self.handler.eventmgr.push_event(event.OrderCreated(order_id=order.id))


@Command.register
class OrderAssign(Command):
    """Subscribe to receive an(other)? order."""
    @classmethod
    def parse_params(cls, **kwargs):
        return {}

    def execute(self):
        self.handler.eventmgr.push_event(
            event.OrderWaiting()  # TODO worker info in params
        )
        self.handler.ordermgr.subscribe(self.handler)


@Command.register
class OrderComplete(Command):
    """Report completion of an order."""
    @classmethod
    def parse_params(cls, *, order_id):
        try:
            return {'order_id': str(uuid.UUID(order_id))}
        except ValueError as e:
            raise error.ParamError(str(e)) from e

    def execute(self, *, order_id):
        self.handler.ordermgr.complete_order_id(order_id)
        self.handler.eventmgr.push_event(
            event.OrderCompleted(order_id=order_id)
        )


@Command.register
class OrderUnassign(Command):
    """Unassign the specified order."""


@Command.register
class OrderCancel(Command):
    """Cancel the specified order."""
