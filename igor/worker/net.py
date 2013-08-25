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
import logging
import json
import multiprocessing
import traceback
import uuid

from .. import order
from ..server import error

logger = logging.getLogger(__name__)


class Worker(asynchat.async_chat):
    def __init__(self, *, pool, host, port):
        super().__init__()
        self.pool = pool
        self.uuid = uuid.uuid4()
        self.create_socket()
        self.connect((host, port))
        self.ibuf = []
        self.set_terminator(b'\n')

        logger.info('worker id: {}'.format(self.uuid))

        for i in range(multiprocessing.cpu_count()):
            self._register_assign()

    def handle_close(self):
        self.close()

    def collect_incoming_data(self, data):
        self.ibuf.append(data)

    def found_terminator(self):
        data = b''.join(self.ibuf)
        self.ibuf = []

        obj = None
        try:
            self.process_data(data)
        except Exception as e:
            logger.exception('unhandled exception')

    def _register_assign(self):
        self.push_obj({'command': 'orderassign'})

    def push_obj(self, obj):
        """Serialise the object as UTF-8 encoded JSON and send."""
        self.push(json.dumps(obj).encode('UTF-8') + b'\n')

    def process_data(self, data):
        try:
            obj = json.loads(data.decode('UTF-8'))
        except Exception as e:
            raise error.ClientError(str(e)) from e
        self.process_obj(obj)

    def process_obj(self, obj):
        if 'order' not in obj:
            logger.warn('received obj that is not an order; ignoring: {}'
                    .format(obj))
        else:
            logger.info('received order: {}'.format(obj))
            o = order.Order.from_obj(obj['order'])
            # TODO check order is assigned and not complete

            def success_cb(result):
                self.push_obj(result)
                self._register_assign()

            def error_cb(e):
                # TODO report build failure to server
                logger.error("Error in worker process:\n{}".format(e.args[0]))
                self.push_obj(build_ordercomplete_obj(o.id))
                self._register_assign()

            self.pool.apply_async(
                work, (o,), {},
                callback=success_cb,
                error_callback=error_cb
            )


def build_ordercomplete_obj(order_id):
    return {
        'command': 'ordercomplete',
        'params': {'order_id': order_id},
    }


# TODO: can open a socket in each worker to send progress to server,
# when we get around to implementing that.  It should be possible to
# share any secrets that authenticate transmissions with the child
# processes.
#
def work(order):
    """Execute a build order.

    This routine cannot be a method on ``Worker`` as it must be
    picklable to work with ``multiprocessing``.

    """
    try:
        order.execute()
    except Exception as e:
        raise RuntimeError(traceback.format_exc())
    return build_ordercomplete_obj(order.id)
