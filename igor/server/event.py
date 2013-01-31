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


class Event:
    events = {}

    @classmethod
    def register(cls, event):
        name = event.name().lower()
        if name not in cls.events:
            cls.events[name] = event
            return event
        elif cls.events[name] is not event:
            raise KeyError("Event name {!r} already registered".format(name))

    @classmethod
    def lookup(cls, name):
        return cls.events[str(name).lower()]

    @classmethod
    def name(cls):
        """Return the name of the event.

        This base implementation returns the name of the class.
        Subclasses for which this does not hold must override this
        class method.

        """
        return cls.__name__

    def __init__(self, **kwargs):
        self.params = kwargs

    def __eq__(self, other):
        return type(self) is type(other) and self.params == other.params

    def __ne__(self, other):
        return not self == other

    def to_obj(self):
        return {'event': self.name(), 'params': self.params}


for name in {
    'Subscribe', 'Unsubscribe',
    'OrderCreated', 'OrderWaiting', 'OrderAssigned', 'OrderCompleted',
    'OrderUnassigned', 'OrderCancelled',
}:
    exec('@Event.register\nclass {}(Event): pass'.format(name))
