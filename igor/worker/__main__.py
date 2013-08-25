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

import argparse
import asyncore
import logging
import multiprocessing
import sys

from . import net


def main():
    parser = argparse.ArgumentParser(description='igor-ci worker')
    parser.add_argument(
        '--host', required=True,
        help='hostname of igor-ci server')
    parser.add_argument(
        '--port', type=int, default=1602,
        help='port of igor-ci server')
    parser.add_argument('--logging', metavar='LEVEL')
    args = parser.parse_args()

    if args.logging:
        try:
            level = getattr(logging, args.logging.upper())
        except AttributeError:
            level = logging.INFO
        logging.basicConfig(level=level)

    with multiprocessing.Pool() as pool:
        worker = net.Worker(pool=pool, host=args.host, port=args.port)
        asyncore.loop()

main()
