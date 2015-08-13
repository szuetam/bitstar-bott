#!/usr/bin/env python
# -*- coding: utf-8 -*-
from decimal import Decimal
import hashlib
import hmac
import json
import logging
import logging.config
import signal
import random
import time

import tornadoredis
from tornado.gen import coroutine, Task
from tornado.ioloop import IOLoop

from backends.base import BaseClient
from config import ACCOUNT_NO, KEY, SECRET

log = logging.getLogger(__name__)
log.setLevel('DEBUG')

redis_client = tornadoredis.Client()
redis_client.connect()

random.seed()


class BitstarClient(BaseClient):
    FIAT_CURRENCY = 'PLN'
    CRYPTO_CURRENCY = 'BTC'
    NETLOC = 'www.bitstar.pl'

    def __init__(self, key=None, secret=None, account_no=None):
        super().__init__()
        credentials = [account_no, key, secret]
        assert all(credentials) or not any(credentials)
        self.nonce = int(time.time())
        self._set_auth(*credentials)

    def _set_auth(self, account_no, key, secret):
        self._account_no = account_no
        self._key = key
        self._secret = secret

    def get_nonce(self):
        self.nonce += 1
        return str(self.nonce)

    def _get_auth_params(self):
        nonce = self.get_nonce()
        msg = ''.join([nonce, self._account_no, self._key]).encode('utf-8')
        signature = hmac.new(self._secret.encode('utf-8'), msg=msg, digestmod=hashlib.sha256).hexdigest().upper()
        params = {
            'key': self._key,
            'nonce': nonce,
            'signature': signature
        }
        return params

    def order_book(self, currency_from=FIAT_CURRENCY, currency_to=CRYPTO_CURRENCY, callback=None):
        params = {
            'currency_from': currency_from,
            'currency_to': currency_to
        }
        return self._get('api/order-book/',
                         callback=callback,
                         params=params)

    def get_balance(self, currency=FIAT_CURRENCY, callback=None):
        params = self._get_auth_params()
        params.update({'currency': currency})
        return self._get('/api/balance/',
                         callback=callback,
                         params=params)

    def place_order_limit(self, base_currency=FIAT_CURRENCY, additional_currency=CRYPTO_CURRENCY,
                    operation=None, amount=None, price=None, callback=None):
        params = self._get_auth_params()
        params.update(dict(base_currency=base_currency,
                           additional_currency=additional_currency,
                           operation=operation,
                           amount=amount,
                           price=price))
        return self._get('/api/place-order-limit/', callback=callback, params=params)

    def cancel_order(self, order_id=None, callback=None):
        params = self._get_auth_params()
        params.update({'order_id': order_id})
        return self._get('/api/cancel-order/', params=params, callback=callback)

    def order_status(self, order_id=None, callback=None):
        params = self._get_auth_params()
        params.update({'order_id': order_id})
        return self._get('/api/order-status/', params=params, callback=callback)

    def open_orders(self, callback=None):
        return self._get('/api/open-orders/', params=self._get_auth_params(), callback=callback)


bbackend = BitstarClient(KEY, SECRET, ACCOUNT_NO)


class Worker:
    """Abstract async worker"""
    timeout = 3

    def __init__(self):
        self.log = log.getChild(type(self).__name__.replace('Watcher', ''))
        self.reset()
        self.is_running = False

    @property
    def successes(self):
        return self.iterations - self.failures

    @coroutine
    def work(self):
        raise NotImplementedError

    def run_once(self):
        return self.run_forever(until_number_of_successes=1)

    @coroutine
    def run_forever(self, until_number_of_successes=None):
        assert not self.is_running
        self.reset()
        self.is_running = True

        if until_number_of_successes is not None:
            self.log.info('running until %s successes',
                          until_number_of_successes)
        else:
            self.log.info('running forever')

        while not self.should_stop:
            try:
                print(IOLoop.instance()._callbacks)
                result = yield self.work()
            except Exception as e:
                result = None
                self.failures += 1
                self.log.exception('work failed')
                self.log.info('will try again')
            else:
                self.log.debug('work success')
            finally:
                self.iterations += 1

            if (until_number_of_successes is not None
                    and self.successes >= until_number_of_successes):
                self.stop()
                self.is_running = False
                # Only really useful with until_number_of_successes=1
                return result
            else:
                yield self.sleep()
            print(IOLoop.instance()._callbacks)

    def stop(self):
        self.log.info('stopping')
        self.should_stop = True

    def reset(self):
        self.should_stop = False
        self.iterations = 0
        self.failures = 0

    # def publish(self, model_or_models):
    #     if isinstance(model_or_models, QuerySet):
    #         models = list(model_or_models)
    #     elif not isinstance(model_or_models, list):
    #         models = [model_or_models]
    #     else:
    #         models = model_or_models
    #     model = models[0]
    #     serializer_class = serializers.MAPPING[type(model)]
    #     msg = json.dumps({
    #         'type': type(model).__name__,
    #         'models': serializer_class(models, many=True).data
    #     })
    #     self.log.debug('publishing change "%s": %s', msg)
    #     redis_client.publish('model_changes', msg)

    @coroutine
    def sleep(self):
        self.log.debug('sleeping for %d seconds', self.timeout)
        yield Task(IOLoop.instance().add_timeout,
                   IOLoop.instance().time() + self.timeout)
        self.log.debug('woken up')


class BalanceWatcher(Worker):
    timeout = 3

    @staticmethod
    def cback(response):
        self.log.debug('Invoked cb')
        print(response)

    @coroutine
    def work(self):
        self.log.debug('fetching balance')
        BTC_balance = yield Task(bbackend.get_balance, 'BTC')
        PLN_balance = yield Task(bbackend.get_balance, 'PLN')
        yield Task(redis_client.set, 'BTC_balance', str(json.dumps(BTC_balance)))
        yield Task(redis_client.set, 'PLN_balance', str(json.dumps(PLN_balance)))
        self.log.debug('balance fetched')


class OrderBookWatcher(Worker):
    timeout = 5

    @coroutine
    def work(self):
        order_book = yield Task(bbackend.order_book)
        yield Task(redis_client.set, 'order_book', str(json.dumps(order_book)))

class OfferCleanerWatcher(Worker):

    @coroutine
    def work(self):
        open_orders = yield Task(bbackend.open_orders)
        # self.log.debug('Cancelling open orders: %s', open_orders)
        for order in open_orders['result']:
            # cancel_id = order['id'].split(':')[1]
            cancel_id = order['id']
            self.log.debug('Cancelling order with id %s: %s', cancel_id, order)
            cancel_result = yield Task(bbackend.cancel_order, cancel_id)
            while cancel_result['status'] != 'ok':
                self.log.debug('Retrying cancel of offer %s', cancel_id)
                cancel_result = yield Task(bbackend.cancel_order, cancel_id)


class Trader(Worker):
    timeout = 60

    @coroutine
    def is_order_done(self, order_id):
        order_status = yield Task(bbackend.order_status, order_id)
        order_status = json.loads(order_status)
        if order_status[order_id]['status'] in ('done', 'rejected',):
            return True
        return False

    @coroutine
    def should_trade(self):
        open_orders = yield Task(bbackend.open_orders)
        if open_orders['result']:
            return False
        return random.choice([True, False])

    @coroutine
    def work(self):
        PLN_balance = yield Task(redis_client.get, 'PLN_balance')
        BTC_balance = yield Task(redis_client.get, 'BTC_balance')

        order_book = yield Task(redis_client.get, 'order_book')
        json_ob = json.loads(order_book)
        PLN_balance = json.loads(PLN_balance)
        BTC_balance = json.loads(BTC_balance)
        self.log.debug('balance %s PLN %s BTC', PLN_balance['result'], BTC_balance['result'])

        best_sell = json_ob['result']['sell'][0]
        best_buy = json_ob['result']['buy'][0]
        self.log.debug('Best sell %s, best buy %s', best_sell, best_buy)

        spread = best_sell['price'] - best_buy['price']
        self.log.debug('Spread %s', spread)

        multiplier_buy = random.randrange(10, 1000)/1000
        delta_buy = spread * multiplier_buy
        buy_price = best_buy['price'] + delta_buy
        multiplier_sell = random.randrange(10, 1000)/1000
        sell_price = buy_price - delta_buy * multiplier_sell
        sell_price = Decimal(sell_price).quantize(Decimal('0.00000001'))
        buy_price = Decimal(buy_price).quantize(Decimal('0.00000001'))

        active_buy_order = yield Task(redis_client.get, 'active_buy_order')
        active_sell_order = yield Task(redis_client.get, 'active_sell_order')
        if active_buy_order is None:
            active_buy_order = json.dumps({'result': ''})
        if active_sell_order is None:
            active_sell_order = json.dumps({'result': ''})

        self.log.debug('active buy order %s', active_buy_order)
        self.log.debug('active sell order %s', active_sell_order)

        should_trade = yield self.should_trade()
        # should_trade = random.choice([True, False])
        self.log.debug('Should trade: %s', should_trade)
        if should_trade:
            # try:
            buy_order = yield Task(bbackend.place_order_limit, **{'operation': 'BID', 'amount': 0.001, 'price': buy_price})
            self.log.debug('Buy order: %s', buy_order)
            sell_order = yield Task(bbackend.place_order_limit, **{'operation': 'ASK', 'amount': 0.001, 'price': sell_price})
            self.log.debug('Sell order: %s', sell_order)

        assert sell_price < buy_price

    @coroutine
    def sleep(self):
        timeout_delta = random.randrange(-30, 31)
        self.log.debug('sleeping for %d seconds', self.timeout + timeout_delta)
        yield Task(IOLoop.instance().add_timeout,
                   IOLoop.instance().time() + self.timeout + timeout_delta)
        self.log.debug('woken up')


@coroutine
def main_loop():
    log.info('starting main loop')
    workers = [BalanceWatcher(), OrderBookWatcher(), Trader(), OfferCleanerWatcher()]

    for worker in workers:
        yield worker.run_once()

    yield [worker.run_forever() for worker in workers]


@coroutine
def cancel_offers_and_exit():
    cleaner = OfferCleanerWatcher()
    log.info('Received ^C cleaning active offers and exitting')
    yield cleaner.run_once()
    IOLoop.instance().stop()
    log.info('Ioloop stopped. Bye')


def main():
    ioloop = IOLoop.instance()
    ioloop.set_blocking_log_threshold(0.2)
    signal.signal(signal.SIGINT, lambda signum, stack: ioloop.add_callback_from_signal(cancel_offers_and_exit))
    ioloop.instance().run_sync(main_loop)


if __name__ == '__main__':
    log.info('*** main() ***')
    main()