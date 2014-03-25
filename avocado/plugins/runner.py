"""
Base Test Runner Plugins.
"""

import os

from avocado.plugins import plugin
from avocado.core import data_dir
from avocado.core import output
from avocado import sysinfo
from avocado import job


class TestLister(plugin.Plugin):

    """
    Implements the avocado 'list' functionality.
    """

    def configure(self, parser):
        """
        Add the subparser for the list action.

        :param parser: Main test runner parser.
        """
        myparser = parser.add_parser('list',
                                     help='List available test modules')
        myparser.set_defaults(func=self.list_tests)
        self.enabled = True

    def list_tests(self, args):
        """
        List available test modules.

        :param args: Command line args received from the list subparser.
        """
        bcolors = output.colors
        pipe = output.get_paginator()
        test_dirs = os.listdir(data_dir.get_test_dir())
        pipe.write(bcolors.header_str('Tests available:'))
        pipe.write("\n")
        for test_dir in test_dirs:
            pipe.write("    %s\n" % test_dir)


class TestRunner(plugin.Plugin):

    """
    Implements the avocado 'run' functionality.
    """

    def configure(self, parser):
        """
        Add the subparser for the run action.

        :param parser: Main test runner parser.
        """
        myparser = parser.add_parser('run', help=('Run a list of test modules '
                                                  'or dropin tests '
                                                  '(space separated)'))
        myparser.add_argument('url', type=str,
                              help=('Test module names or paths to dropin tests '
                                    '(space separated)'),
                              nargs='?', default='')
        myparser.set_defaults(func=self.run_tests)
        self.enabled = True

    def run_tests(self, args):
        """
        Run test modules or dropin tests.

        :param args: Command line args received from the run subparser.
        """
        job_instance = job.Job(args)
        job_instance.run()


class SystemInformation(plugin.Plugin):

    """
    Collect system information and log.
    """

    def configure(self, parser):
        """
        Add the subparser for the run action.

        :param parser: Main test runner parser.
        """
        myparser = parser.add_parser('sysinfo',
                                     help='Collect system information')
        myparser.add_argument('sysinfodir', type=str,
                              help='Dir where to dump sysinfo',
                              nargs='?', default='')
        myparser.set_defaults(func=sysinfo.collect_sysinfo)
        self.enabled = True
