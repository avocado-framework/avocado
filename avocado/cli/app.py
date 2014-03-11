"""
Implements the base avocado runner application.
"""
import imp
import logging
import os
from argparse import ArgumentParser

from avocado import sysinfo
from avocado.core import data_dir
from avocado.core import output

log = logging.getLogger("avocado.app")


def run_tests(args):
    """
    Find test modules in tests dir and run them.

    :param args: Command line arguments.
    """
    output_manager = output.OutputManager()
    urls = args.url.split()
    total_tests = len(urls)
    test_dir = data_dir.get_test_dir()
    output_manager.log_header("TESTS DIR: %s" % test_dir)
    output_manager.log_header("TOTAL TESTS: %s" % total_tests)
    output_mapping = {'PASS': output_manager.log_pass,
                      'FAIL': output_manager.log_fail,
                      'TEST_NA': output_manager.log_skip,
                      'WARN': output_manager.log_warn}

    test_index = 1

    for url in urls:
        test_module_dir = os.path.join(test_dir, url)
        f, p, d = imp.find_module(url, [test_module_dir])
        test_module = imp.load_module(url, f, p, d)
        f.close()
        test_class = getattr(test_module, url)
        test_instance = test_class(name=url)
        test_instance.run()
        output_func = output_mapping[test_instance.status]
        label = "(%s/%s) %s:" % (test_index, total_tests, test_instance.name)
        output_func(label, test_instance.time_elapsed)
        test_index += 1


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

        prun = subparsers.add_parser('run', help='Run a single test module')
        prun.add_argument('url', type=str,
                          help='Test module names (space separated)',
                          nargs='?', default='')
        prun.set_defaults(func=run_tests)

        psysinfo = subparsers.add_parser('sysinfo',
                                         help='Collect system information')
        psysinfo.add_argument('sysinfodir', type=str,
                              help='Dir where to dump sysinfo',
                              nargs='?', default='')
        psysinfo.set_defaults(func=sysinfo.collect_sysinfo)

        self.args = self.arg_parser.parse_args()

    def run(self):
        self.args.func(self.args)
