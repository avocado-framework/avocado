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
# Copyright: (c) 2013-2015 Red Hat
# Author: Cleber Rosa <cleber@redhat.com>

"""
This is the main entry point for the rest client cli application
"""


import sys
import logging
import importlib
import functools

from avocado import settings
from avocado.core import exit_codes
from avocado.restclient import connection
from avocado.restclient.cli import parser

__all__ = ['App']


class App(object):

    """
    Base class for CLI application
    """

    def __init__(self):
        """
        Initializes a new app instance.

        This class is intended both to be used by the stock arcli application
        and also to be reused by custom applications. If you want, say, to
        limit the amount of command line actions and its arguments, you can
        simply supply another argument parser class to this constructor. Of
        course another way to customize it is to inherit from this and modify
        its members at will.
        """
        self.connection = None
        self.parser = parser.Parser()
        self.parser.add_arguments_on_all_modules()

    def initialize_connection(self):
        """
        Initialize the connection instance
        """
        try:
            self.connection = connection.Connection()
        except connection.InvalidConnectionError:
            logging.error("Could not connect to the server")
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)
        except connection.InvalidServerVersionError:
            logging.error("The REST server version is more recent than "
                          "this version of the REST client can support. "
                          "Please use a more recent version of the REST "
                          "client application.")
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)

    def dispatch_action(self):
        """
        Calls the actions that was specified via command line arguments.

        This involves loading the relevant module file.
        """
        module_name = "%s.%s" % ('avocado.restclient.cli.actions',
                                 self.args.top_level_action)
        logging.debug("Attempting to load action module: %s", module_name)

        try:
            module = importlib.import_module(module_name)
            logging.debug("Action module loaded: %s", module)
        except ImportError:
            logging.critical("Could not load action module: %s", module_name)
            return

        # Filter out the attributes out of the loaded module that look
        # like command line actions, based on type and 'is_action' attribute
        module_actions = {}
        for attribute_name in module.__dict__:
            attribute = module.__dict__[attribute_name]
            module_actions[attribute_name] = attribute

        chosen_action = None
        for action in module_actions.keys():
            if getattr(self.args, action, False):
                logging.debug("Calling action %s from module %s",
                              action, module_name)
                chosen_action = action
                break

        kallable = module_actions.get(chosen_action, None)
        if kallable is not None:
            self.initialize_connection()
            return kallable(self)
        else:
            logging.error("Action specified is not implemented")

    def run(self):
        """
        Main entry point for application
        """
        action_result = None
        try:
            self.args = self.parser.parse_args()
            action_result = self.dispatch_action()
        except KeyboardInterrupt:
            print 'Interrupted'
        if isinstance(action_result, int):
            sys.exit(action_result)
        elif isinstance(action_result, bool):
            if action_result is True:
                sys.exit(0)
            else:
                sys.exit(1)
