"""
Implements the base avocado runner application.
"""
import imp
import logging
import os
import time
from argparse import ArgumentParser

from avocado import sysinfo
from avocado.plugins.manager import get_plugin_manager


class AvocadoRunnerApp(object):

    """
    Basic avocado runner application.
    """

    def __init__(self):
        self.plugin_manager = None
        self.arg_parser = ArgumentParser(description='Avocado Test Runner')
        self.arg_parser.add_argument('-v', '--verbose', action='store_true',
                                     help='print extra debug messages',
                                     dest='verbose')
        self.arg_parser.add_argument('--logdir', action='store',
                                     help='Alternate logs directory',
                                     dest='logdir', default='')
        self.arg_parser.add_argument('--loglevel', action='store',
                                     help='Debug Level',
                                     dest='log_level', default='')

        subparsers = self.arg_parser.add_subparsers(title='subcommands',
                                                    description='valid subcommands',
                                                    help='subcommand help')

        psysinfo = subparsers.add_parser('sysinfo',
                                         help='Collect system information')
        psysinfo.add_argument('sysinfodir', type=str,
                              help='Dir where to dump sysinfo',
                              nargs='?', default='')
        psysinfo.set_defaults(func=sysinfo.collect_sysinfo)

        self.load_plugin_manager(subparsers)
        self.args = self.arg_parser.parse_args()

    def load_plugin_manager(self, parser):
        self.plugin_manager = get_plugin_manager()
        self.plugin_manager.load_plugins()
        self.plugin_manager.configure(parser)

    def run(self):
        self.args.func(self.args)
