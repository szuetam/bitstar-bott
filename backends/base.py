#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import urllib.parse

from tornado.httpclient import AsyncHTTPClient, HTTPClient, HTTPRequest


class ClientError(Exception):
    pass


class BaseClient(object):
    SCHEME = 'https'

    def _build_url(self, path, params=None):
        print('build', '*'*20, path, self.NETLOC)
        if isinstance(params, dict):
            params = urllib.parse.urlencode(params)
        return urllib.parse.urlunsplit((self.SCHEME, self.NETLOC, path, params, None,))

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

    def _request(self, method, path, callback=None, body=None):
        request = HTTPRequest(path, method=method, body=body)

        # client_class = AsyncHTTPClient if callback else HTTPClient
        # client = client_class()

        if callback:
            return AsyncHTTPClient().fetch(request=request,
                                callback=lambda resp: callback(self._process_response(resp)))
        else:
            return self._process_response(HTTPClient().fetch(request))

    def _get(self, path, callback=None, params=None):
        print('*'*20, path)
        path = self._build_url(path, params)
        return self._request('GET', path=path, callback=callback)
