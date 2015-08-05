#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import logging.config

from tornado.gen import coroutine
from tornado.ioloop import IOLoop

from config import LOGGING
from backends.bitstar import BalanceWatcher, OrderBookWatcher, Trader, OfferCleanerWatcher

log = logging.getLogger(__name__)
logging.config.dictConfig(LOGGING)
log.setLevel('DEBUG')

@coroutine
def main_loop():
    log.info('starting main loop')
    workers = [BalanceWatcher(), OrderBookWatcher(), Trader(), OfferCleanerWatcher()]

    for worker in workers:
        yield worker.run_once()

    yield [worker.run_forever() for worker in workers]


def main():
    try:
        IOLoop.instance().set_blocking_log_threshold(0.1)
        IOLoop.instance().run_sync(main_loop)
    except KeyboardInterrupt:
        log.info('^C, quitting.')

if __name__ == '__main__':
    log.info('*** main() ***')
    main()