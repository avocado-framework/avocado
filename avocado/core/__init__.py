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


from .dispatcher import InitDispatcher
from .future.settings import settings as future_settings
from .output import BUILTIN_STREAMS, BUILTIN_STREAM_SETS


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


def initialize_plugins():
    InitDispatcher().map_method('initialize')


register_core_options()
initialize_plugins()
