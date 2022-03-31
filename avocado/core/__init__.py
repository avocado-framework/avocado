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

import pkg_resources

from avocado.core.dispatcher import InitDispatcher
from avocado.core.settings import settings as stgs
from avocado.core.streams import BUILTIN_STREAM_SETS, BUILTIN_STREAMS
from avocado.core.utils.path import prepend_base_path


def register_core_options():
    streams = (['"%s": %s' % _ for _ in BUILTIN_STREAMS.items()] +  # pylint: disable=C0209
               ['"%s": %s' % _ for _ in BUILTIN_STREAM_SETS.items()])  # pylint: disable=C0209
    streams = "; ".join(streams)
    help_msg = (f"List of comma separated builtin logs, or logging streams "
                f"optionally followed by LEVEL (DEBUG,INFO,...). Builtin "
                f"streams are: {streams}. By default: 'app'")
    stgs.register_option(section='core',
                         key='show',
                         key_type=lambda x: set(x.split(',')),
                         metavar="STREAM[:LVL]",
                         nargs='?',
                         default=set(["app"]),
                         help_msg=help_msg)

    help_msg = ('Python regular expression that will make the test '
                'status WARN when matched.')
    stgs.register_option(section='simpletests.status',
                         key='warn_regex',
                         default='^WARN$',
                         help_msg=help_msg)

    help_msg = ('Location to search the regular expression on. '
                'Accepted values: all, stdout, stderr.')
    stgs.register_option(section='simpletests.status',
                         key='warn_location',
                         default='all',
                         help_msg=help_msg)

    help_msg = ('Python regular expression that will make the test '
                'status SKIP when matched.')
    stgs.register_option(section='simpletests.status',
                         key='skip_regex',
                         default='^SKIP$',
                         help_msg=help_msg)

    help_msg = ('Location to search the regular expression on. '
                'Accepted values: all, stdout, stderr.')
    stgs.register_option(section='simpletests.status',
                         key='skip_location',
                         default='all',
                         help_msg=help_msg)

    help_msg = ('Fields to include in the presentation of SIMPLE test '
                'failures.  Accepted values: status, stdout, stderr.')
    stgs.register_option(section='simpletests.status',
                         key='failure_fields',
                         key_type=list,
                         default=['status', 'stdout', 'stderr'],
                         help_msg=help_msg)

    help_msg = ('The amount of time to give to the test process after '
                'it it has been interrupted (such as with CTRL+C)')
    stgs.register_option(section='runner.timeout',
                         key='after_interrupted',
                         key_type=int,
                         help_msg=help_msg,
                         default=60)

    # Let's assume that by default, cache will be located under the user's
    # umbrella. This will make it easy for our deployments and it is a common
    # place for other applications too.
    help_msg = 'Cache directories to be used by the avocado test'
    default = prepend_base_path('~/avocado/data/cache')
    stgs.register_option(section='datadir.paths',
                         key='cache_dirs',
                         key_type=list,
                         default=[default],
                         help_msg=help_msg)

    help_msg = 'Base directory for Avocado tests and auxiliary data'
    default = prepend_base_path('~/avocado')
    stgs.register_option(section='datadir.paths',
                         key='base_dir',
                         key_type=prepend_base_path,
                         default=default,
                         help_msg=help_msg)

    help_msg = 'Test directory for Avocado tests'
    default = prepend_base_path('/usr/share/doc/avocado/tests')
    stgs.register_option(section='datadir.paths',
                         key='test_dir',
                         key_type=prepend_base_path,
                         default=default,
                         help_msg=help_msg)

    help_msg = 'Data directory for Avocado'
    default = prepend_base_path('~/avocado/data')
    stgs.register_option(section='datadir.paths',
                         key='data_dir',
                         key_type=prepend_base_path,
                         default=default,
                         help_msg=help_msg)

    help_msg = 'Logs directory for Avocado'
    default = prepend_base_path('~/avocado/job-results')
    stgs.register_option(section='datadir.paths',
                         key='logs_dir',
                         key_type=prepend_base_path,
                         default=default,
                         help_msg=help_msg)

    help_msg = ('The amount of time to wait after a test has reported '
                'status but the test process has not finished')
    stgs.register_option(section='runner.timeout',
                         key='process_alive',
                         key_type=int,
                         help_msg=help_msg,
                         default=60)

    help_msg = ('The amount of to wait for a test status after the '
                'process has been noticed to be dead')
    stgs.register_option(section='runner.timeout',
                         key='process_died',
                         key_type=int,
                         help_msg=help_msg,
                         default=10)

    help_msg = ('Whether to display colored output in terminals that '
                'support it')
    stgs.register_option(section='runner.output',
                         key='colored',
                         key_type=bool,
                         default=True,
                         help_msg=help_msg)

    help_msg = ('Whether to force colored output to non-tty outputs '
                '(e.g. log files). Allowed values: auto, always, never')
    stgs.register_option(section='runner.output',
                         key='color',
                         default='auto',
                         help_msg=help_msg)

    help_msg = 'Use UTF8 encoding (True or False)'
    stgs.register_option(section='runner.output',
                         key='utf8',
                         key_type=bool,
                         help_msg=help_msg,
                         default=True)

    help_msg = ('Suppress notification about broken plugins in the app '
                'standard error. Add the name of each broken plugin you '
                'want to suppress the notification in the list. (e.g. '
                '"avocado_result_html")')
    stgs.register_option(section='plugins',
                         key='skip_broken_plugin_notification',
                         key_type=list,
                         default=[],
                         help_msg=help_msg)

    help_msg = 'The encoding used by default on all data input'
    stgs.register_option(section='core',
                         key='input_encoding',
                         default='utf-8',
                         help_msg=help_msg)

    # All settings starting with 'runner.' will be passed to runner
    # exec-test runner config
    help_msg = ('Use a custom exit code list to consider a test as skipped. '
                'This is only used by exec-test runners. Default is [].')
    stgs.register_option(section='runner.exectest.exitcodes',
                         key='skip',
                         default=[],
                         key_type=list,
                         help_msg=help_msg)

    help_msg = ('By default Avocado runners will use the {uri} of a test as '
                'its identifier. Use a custom f-string identifier in order to '
                'change it.')
    stgs.register_option(section='runner',
                         key='identifier_format',
                         default="{uri}",
                         help_msg=help_msg)

    help_msg = 'List of test references (aliases or paths)'
    stgs.register_option(section='resolver',
                         key='references',
                         key_type=list,
                         default=[],
                         help_msg=help_msg)

    help_msg = ('Selects the runner implementation from one of the '
                'installed and active implementations.  You can run '
                '"avocado plugins" and find the list of valid runners '
                'under the "Plugins that run test suites on a job '
                '(runners) section.  Defaults to "nrunner", which is '
                'the new runner and only runner supported at this moment.')
    stgs.register_option(section='run',
                         key='test_runner',
                         default='nrunner',
                         help_msg=help_msg)


def initialize_plugin_infrastructure():
    help_msg = 'Plugins that will not be loaded and executed'
    stgs.register_option(section='plugins',
                         key='disable',
                         key_type=list,
                         default=[],
                         help_msg=help_msg)

    kinds = list(pkg_resources.get_entry_map('avocado-framework').keys())
    plugin_types = [kind[8:] for kind in kinds
                    if kind.startswith('avocado.plugins.')]
    for plugin_type in plugin_types:
        help_msg = f'Execution order for "{plugin_type}" plugins'
        stgs.register_option(section=plugin_type,
                             key='order',
                             key_type=list,
                             default=[],
                             help_msg=help_msg)


def initialize_plugins():
    initialize_plugin_infrastructure()
    InitDispatcher().map_method('initialize')
