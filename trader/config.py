#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

KEY = '7181723051:Cbv95T8JwX0a5n8Zs7e4UHiJ1Ssu9f4KwF3I'
SECRET = 'X3eNwt5Eu89TyLf95oq6YGM8f93FB45OpVxg'
ACCOUNT_NO = '7181723051'


LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(name)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(name)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file_log': {
            'level': 'DEBUG',
            'class': 'logging.handlers.WatchedFileHandler',
            'encoding': 'utf-8',
            'filename': os.path.join(BASE_DIR, 'trader.log'),
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file_log', 'console'],
        'level': 'DEBUG',
        'propagate': True
    },
}