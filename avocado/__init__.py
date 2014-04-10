# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: RedHat 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

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
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}


logging.config.dictConfig(DEFAULT_LOGGING)
