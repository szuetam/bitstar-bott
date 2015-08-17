#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

import tornado.ioloop
import tornado.web
from tornado.options import define, options, parse_command_line
import tornadoredis
import tornadoredis.pubsub
from sockjs.tornado import SockJSConnection, SockJSRouter

import settings

log = logging.getLogger(__name__)
subscriber = tornadoredis.pubsub.SockJSSubscriber(tornadoredis.Client())

define('port', type=int, default=8000)

class ChangesConnection(SockJSConnection):
    CHANNELS = ['monitoring', 'changes']

    def on_open(self, info):
        log.info('on_open')
        subscriber.subscribe(self.CHANNELS, self)

    def on_close(self):
        log.info('on_close')
        subscriber.unsubscribe(self.CHANNELS, self)

router = SockJSRouter(ChangesConnection, '/realtime/changes')
urls = router.urls

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')


def main():
    parse_command_line()
    tornado_app = tornado.web.Application(
        debug=settings.DEBUG,
        template_path=settings.TEMPLATES_DIR,
        handlers=urls + [(r'/static/(.*)', tornado.web.StaticFileHandler, {'path': settings.STATIC_PATH}), (r'/', MainHandler),]
    )
    tornado_app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()