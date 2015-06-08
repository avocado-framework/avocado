# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>


__all__ = ['configure', 'DEFAULT_LOGGING']


import logging

if hasattr(logging, 'NullHandler'):
    NULL_HANDLER = 'logging.NullHandler'
else:
    NULL_HANDLER = 'logutils.NullHandler'

DEFAULT_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'brief': {
            'format': '%(message)s',
        },
    },
    'filters': {
        'error': {
            '()': 'avocado.core.output.FilterError',
        },
        'info': {
            '()': 'avocado.core.output.FilterInfo',
        },
    },
    'handlers': {
        'null': {
            'level': 'INFO',
            'class': NULL_HANDLER,
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'brief',
        },
        'app': {
            'level': 'INFO',
            'class': 'avocado.core.output.ProgressStreamHandler',
            'formatter': 'brief',
            'filters': ['info'],
            'stream': 'ext://sys.stdout',
        },
        'error': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'brief',
            'filters': ['error'],
        },
        'debug': {
            'level': 'DEBUG',
            'class': 'avocado.core.output.ProgressStreamHandler',
            'formatter': 'brief',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        'avocado': {
            'handlers': ['console'],
        },
        'avocado.app': {
            'handlers': ['app', 'error'],
            'level': 'INFO',
            'propagate': False,
        },
        'avocado.test': {
            'handlers': ['null'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'avocado.test.stdout': {
            'handlers': ['null'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'avocado.test.stderr': {
            'handlers': ['null'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'avocado.sysinfo': {
            'handlers': ['error'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'avocado.debug': {
            'handlers': ['debug'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}


def configure(logging_config=DEFAULT_LOGGING):
    from logging import config
    if not hasattr(config, 'dictConfig'):
        from logutils import dictconfig
        cfg_func = dictconfig.dictConfig
    else:
        cfg_func = config.dictConfig
    cfg_func(logging_config)
