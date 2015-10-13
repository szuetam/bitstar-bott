#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import logging.config
import signal

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
    workers = [Trader(), OfferCleanerWatcher()]
    #workers = [BalanceWatcher(), OfferCleanerWatcher()]

    for worker in workers:
        yield worker.run_once()

    yield [worker.run_forever() for worker in workers]


@coroutine
def cancel_offers_and_exit():
    print('Received ^C cleaning active offers and exitting')
    cleaner = OfferCleanerWatcher()
    yield cleaner.run_once()
    IOLoop.instance().stop()
    print('Ioloop stopped. Bye')


def main():
    ioloop = IOLoop.instance()
    ioloop.set_blocking_log_threshold(0.2)
    signal.signal(signal.SIGINT, lambda signum, stack: ioloop.add_callback_from_signal(cancel_offers_and_exit))
    ioloop.instance().run_sync(main_loop)

if __name__ == '__main__':
    log.info('*** main() ***')
    main()
