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


import os

from .dispatcher import InitDispatcher
from .future.settings import settings as future_settings
from .output import BUILTIN_STREAMS, BUILTIN_STREAM_SETS
from .utils import prepend_base_path


def register_core_options():
    streams = (['"%s": %s' % _ for _ in BUILTIN_STREAMS.items()] +
               ['"%s": %s' % _ for _ in BUILTIN_STREAM_SETS.items()])
    streams = "; ".join(streams)
    help_msg = ("List of comma separated builtin logs, or logging streams "
                "optionally followed by LEVEL (DEBUG,INFO,...). Builtin "
                "streams are: %s. By default: 'app'" % streams)
    future_settings.register_option(section='core',
                                    key='show',
                                    key_type=lambda x: x.split(','),
                                    metavar="STREAM[:LVL]",
                                    nargs='?',
                                    default=['app'],
                                    help_msg=help_msg)

    help_msg = ('Python regular expression that will make the test '
                'status WARN when matched.')
    future_settings.register_option(section='simpletests.status',
                                    key='warn_regex',
                                    default='^WARN$',
                                    help_msg=help_msg)

    help_msg = ('Location to search the regular expression on. '
                'Accepted values: all, stdout, stderr.')
    future_settings.register_option(section='simpletests.status',
                                    key='warn_location',
                                    default='all',
                                    help_msg=help_msg)

    help_msg = ('Python regular expression that will make the test '
                'status SKIP when matched.')
    future_settings.register_option(section='simpletests.status',
                                    key='skip_regex',
                                    default='^SKIP$',
                                    help_msg=help_msg)

    help_msg = ('Location to search the regular expression on. '
                'Accepted values: all, stdout, stderr.')
    future_settings.register_option(section='simpletests.status',
                                    key='skip_location',
                                    default='all',
                                    help_msg=help_msg)

    help_msg = ('The amount of time to give to the test process after '
                'it it has been interrupted (such as with CTRL+C)')
    future_settings.register_option(section='runner.timeout',
                                    key='after_interrupted',
                                    key_type=int,
                                    help_msg=help_msg,
                                    default=60)

    help_msg = 'Cache directories to be used by the avocado test'
    future_settings.register_option(section='datadir.paths',
                                    key='cache_dirs',
                                    key_type=list,
                                    default=[],
                                    help_msg=help_msg)

    help_msg = 'Base directory for Avocado tests and auxiliary data'
    default = prepend_base_path('/var/lib/avocado')
    future_settings.register_option(section='datadir.paths',
                                    key='base_dir',
                                    key_type=prepend_base_path,
                                    default=default,
                                    help_msg=help_msg)

    help_msg = 'Test directory for Avocado tests'
    default = prepend_base_path('/usr/share/doc/avocado/tests')
    future_settings.register_option(section='datadir.paths',
                                    key='test_dir',
                                    key_type=prepend_base_path,
                                    default=default,
                                    help_msg=help_msg)

    help_msg = 'Data directory for Avocado'
    default = prepend_base_path('/var/lib/avocado/data')
    future_settings.register_option(section='datadir.paths',
                                    key='data_dir',
                                    key_type=prepend_base_path,
                                    default=default,
                                    help_msg=help_msg)

    help_msg = 'Logs directory for Avocado'
    default = prepend_base_path('~/avocado/job-results')
    future_settings.register_option(section='datadir.paths',
                                    key='logs_dir',
                                    key_type=prepend_base_path,
                                    default=default,
                                    help_msg=help_msg)


def initialize_plugins():
    InitDispatcher().map_method('initialize')


register_core_options()
initialize_plugins()
