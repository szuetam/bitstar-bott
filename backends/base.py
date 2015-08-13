#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import json
import logging
import urllib.parse

from tornado.ioloop import IOLoop
from tornado import stack_context
from tornado.concurrent import Future, TracebackFuture
from tornado.httpclient import AsyncHTTPClient, HTTPClient, HTTPRequest

log = logging.getLogger('backends.base')
log.setLevel('DEBUG')

DEFAULT_BURST_WINDOW = datetime.timedelta(seconds=5)
DEFAULT_WAIT_WINDOW = datetime.timedelta(seconds=60)

class ClientError(Exception):
    pass

class BurstThrottle(object):
    max_hits = None
    burst_window = None
    total_window = None
    timestamp = None

    def __init__(self, max_hits, burst_window, wait_window):
        self.max_hits = max_hits
        self.hits = 0
        self.burst_window = burst_window
        self.total_window = burst_window + wait_window
        self.timestamp = datetime.datetime.min
        log.info('Throttler set up: max_hits %s, interval: %s', self.max_hits, self.total_window)

    def throttle(self):
        now = datetime.datetime.utcnow()
        if now < self.timestamp + self.total_window:
            if (now < self.timestamp + self.burst_window) and (self.hits < self.max_hits):
                self.hits += 1
                return False
            else:
                log.info('Throttling - hits: %s', self.hits)
                return True
        else:
            self.timestamp = now
            self.hits = 1
            return False

class AllowanceThrottle(object):

    def __init__(self, rate=10, per=10, allowance=None):
        self.rate = rate
        self.per = per
        self.allowance = allowance or self.rate
        self.timestamp = datetime.datetime.utcnow()

    def throttle(self):
        now = datetime.datetime.utcnow()
        time_passed = now - self.timestamp
        self.timestamp = now
        self.allowance += time_passed.seconds * (self.rate / self.per)
        print(self.allowance)
        if self.allowance > self.rate:
            self.allowance = self.rate
        if self.allowance < 1.0:
            return True
        else:
            self.allowance -= 1.0
            return False


class BaseClient(object):
    SCHEME = 'https'
    NETLOC = None

    def __init__(self, max_requests=60, burst_window=DEFAULT_BURST_WINDOW, wait_window=DEFAULT_WAIT_WINDOW):
        self.throttle = BurstThrottle(max_requests, burst_window, wait_window)

    def _build_url(self, path, params=None):
        if isinstance(params, dict):
            params = urllib.parse.urlencode(params)
        return urllib.parse.urlunsplit((self.SCHEME, self.NETLOC, path, params, None,))

    def should_throttle(self):
        print(self.throttle.hits)
        return self.throttle.throttle()

    def _process_response(self, response):
        response.rethrow()

        # ctype =  response.headers['Content-Type']
        # if 'json' not in ctype:
        #     raise ValueError('not Json response {} {} {}'.format(ctype,
        #                                                          response.headers,
        #                                                          response.body))

        # (kniski) add decode checking

        data = json.loads(response.body.decode('utf-8'))
        if 'errors' in data:
            raise ClientError(data['errors'])

        return data

    def throttled_client(self):
        fut = Future()
        fut.set_result(None)
        return fut

    def return_throttled(self):
        future = TracebackFuture()
        future.set_result('placki')

        # IOLoop.instance().add_callback(stack_context.wrap(throttled_callback))
        return future

    def _request(self, method, path, callback=None, body=None):
        request = HTTPRequest(path, method=method, body=body)

        client_class = AsyncHTTPClient if callback else HTTPClient
        client = client_class()
        print('About to make request')
        if self.should_throttle():
            print('Throttled')
            return self.return_throttled()
        if callback:
            return client.fetch(request=request,
                                callback=lambda resp: callback(self._process_response(resp)))
        else:
            return self._process_response(client.fetch(request))

    def _get(self, path, callback=None, params=None):
        path = self._build_url(path, params)
        return self._request('GET', path=path, callback=callback)
