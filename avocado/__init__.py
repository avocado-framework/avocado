import cli
import core

import job
import test
import version
import linux

import logging.config

DEFAULT_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'brief': {
            'format': '%(message)s',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'brief',
        },
    },
    'loggers': {
        'avocado': {
            'handlers': ['console'],
        },
        'avocado.app': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'avocado.test': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'avocado.utils': {
            'handlers': [],
            'level': 'INFO',
            'propagate': False,
        },
    }
}


logging.config.dictConfig(DEFAULT_LOGGING)
