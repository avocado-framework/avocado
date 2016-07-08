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
# Copyright (c) 2013-2015 Red Hat
# Author: Cleber Rosa <cleber@redhat.com>

"""
REST client application command line parsing
"""

import os
import glob
import argparse
import importlib

from ...version import VERSION


class Parser(argparse.ArgumentParser):

    '''
    The main CLI Argument Parser.
    '''

    def __init__(self, **kwargs):
        '''
        Initializes a new parser
        '''
        super(Parser, self).__init__(
            description='Avocado Rest Client %s' % VERSION,
            **kwargs
        )

        self._subparsers = None
        self._add_global_arguments()

    def _add_global_arguments(self):
        '''
        Add global arguments, that is, do not depend on a specific command
        '''
        connection_group = self.add_argument_group(
            'CONNECTION',
            'Set connection options to an Avocado Server')

        connection_group.add_argument(
            '--hostname',
            help='Hostname or IP address for the avocado server',
            default='localhost')

        connection_group.add_argument(
            '--port',
            help='Port where avocado server is listening on',
            default=9405)

        connection_group.add_argument(
            '--username',
            help='Username to authenticate to avocado server')

        connection_group.add_argument(
            '--password',
            help='Password to give to avocado server')

    def add_arguments_on_all_modules(self,
                                     prefix='avocado.core.restclient.cli.args'):
        '''
        Add arguments that are present on all Python modules at a given prefix

        :param prefix: a Python module namespace
        '''
        blacklist = ('base', '__init__')
        basemod = importlib.import_module(prefix)
        basemod_dir = os.path.dirname(basemod.__file__)

        # FIXME: This works for CPython and IronPython, but not for Jython
        mod_files_pattern = os.path.join(basemod_dir, "*.py")
        mod_files = glob.glob(mod_files_pattern)
        mod_names_with_suffix = [os.path.basename(f) for f in mod_files]
        mod_names = [n.replace(".py", "")
                     for n in mod_names_with_suffix]
        mod_names = [n for n in mod_names if n not in blacklist]

        for module in mod_names:
            self.add_arguments_on_module(module, prefix)

    def add_arguments_on_module(self, name, prefix):
        '''
        Add arguments that are present on a given Python module

        :param name: the name of the Python module, without the namespace
        '''
        if self._subparsers is None:
            self._subparsers = self.add_subparsers(
                prog='avocado-rest-client',
                title='Top Level Command',
                dest='top_level_action'
            )

        module_name = "%s.%s" % (prefix, name)
        module = importlib.import_module(module_name)

        parser = self._subparsers.add_parser(name)

        if hasattr(module, 'ACTION_ARGUMENTS'):
            if module.ACTION_ARGUMENTS:
                act_grp = parser.add_argument_group("ACTION",
                                                    "Action to be performed")
                act_excl = act_grp.add_mutually_exclusive_group(required=True)

                for action in module.ACTION_ARGUMENTS:
                    act_excl.add_argument(*action[0], **action[1])

        if hasattr(module, 'ARGUMENTS'):
            if module.ARGUMENTS:
                for arg in module.ARGUMENTS:
                    # Support either both short+long options or either one, short OR long
                    short_and_or_long_opts = arg[0]
                    if len(short_and_or_long_opts) == 1:
                        parser.add_argument(arg[0][0], **arg[1])
                    else:
                        parser.add_argument(*arg[0], **arg[1])
