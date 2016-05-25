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
# Copyright: Red Hat Inc. 2016
# Author: Amador Pahim <apahim@redhat.com>

import argparse
import os
from .base import CLI
from avocado.core.settings import settings


class EnvVars(CLI):

    """
    Set environment variables
    """

    name = 'envvars'
    description = "Set variables in tests processes environemnt"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        msg = 'environemnt variables'
        replay_parser = run_subcommand_parser.add_argument_group(msg)
        replay_parser.add_argument('--test-env', dest='test_env',
                                   default=None,
                                   type=self._parse_test_env_vars,
                                   help='Set environemnt variables for tests')

    def _parse_test_env_vars(self, string):
        # Convert this:
        #  'key=value,key2=value2,key3=value3'
        # into this:
        #  {'key': 'value', 'key2': 'value2', 'key3': 'value3'}
        try:
            env_dict = {}
            env_list = string.split(',')
            for item in env_list:
                key, value = item.split('=', 1)
                env_dict.update({key: value})
            return env_dict
        except:
            raise argparse.ArgumentTypeError('Invalid format.')

    def run(self, args):
        if getattr(args, 'test_env', None) is None:
            return

        env_vars = settings.get_value('test.environment', 'env_vars',
                                      key_type=list, default=None)
        if env_vars is not None:
            for item in env_vars:
                args.test_env.update(self._parse_test_env_vars(item))

        env_keep = settings.get_value('test.environment', 'env_keep',
                                      key_type=list, default=None)
        if env_keep is not None:
            for key in env_keep:
                value = os.environ.get(key)
                if value is not None:
                    args.test_env.update({key: value})
