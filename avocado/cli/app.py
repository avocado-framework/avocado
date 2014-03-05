"""
Implements the base avocado runner application.
"""
import logging
from argparse import ArgumentParser

log = logging.getLogger("avocado.app")


class AvocadoRunnerApp(object):

    """
    Basic avocado runner application.
    """

    def __init__(self):
        self.arg_parser = ArgumentParser(description='Avocado Test Runner')
        self.arg_parser.add_argument('-v', '--verbose', action='store_true',
                                     help='print extra debug messages',
                                     dest='verbose')

        subparsers = self.arg_parser.add_subparsers(title='subcommands',
                                                    description='valid subcommands',
                                                    help='subcommand help')

        self.args = self.arg_parser.parse_args()

    def run(self):
        self.args.func(self.args)
