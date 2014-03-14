"""Runner Plugins."""

import imp
import logging
import os
import time

from avocado.plugins.plugin import Plugin
from avocado.core import data_dir
from avocado.core import output
from avocado import sysinfo
from avocado import test


class TestListerRunner(Plugin):

    """
    This runner list all tests available.
    """

    def configure(self, parser):
        tlist = parser.add_parser('list',
                                  help='List available test modules')
        tlist.set_defaults(func=self.list_tests)
        self.enabled = True

    def list_tests(self, arguments):
        bcolors = output.colors
        pipe = output.get_paginator()
        test_dirs = os.listdir(data_dir.get_test_dir())
        pipe.write(bcolors.header_str("Tests available:"))
        pipe.write("\n")
        for test_dir in test_dirs:
            pipe.write("    %s\n" % test_dir)


class SimpleTestRunner(Plugin):

    """
    This runner executes tests.
    """

    def configure(self, parser):
        myparser = parser.add_parser('run', help=('Run a single test module '
                                                  'or dropin test'))
        myparser.add_argument('url', type=str,
                              help=('Test module names or paths to dropin tests '
                                    '(space separated)'),
                              nargs='?', default='')
        myparser.set_defaults(func=self.run_tests)

    def run_tests(self, args):
        """
        Find test modules in tests dir and run them.

        :param args: Command line arguments.
        """
        test_start_time = time.strftime('%Y-%m-%d-%H.%M.%S')
        logdir = args.logdir or data_dir.get_logs_dir()
        debugbase = 'run-%s' % test_start_time
        debugdir = os.path.join(logdir, debugbase)
        latestdir = os.path.join(logdir, "latest")
        if not os.path.isdir(debugdir):
            os.makedirs(debugdir)
        try:
            os.unlink(latestdir)
        except OSError:
            pass
        os.symlink(debugbase, latestdir)

        debuglog = os.path.join(debugdir, "debug.log")
        loglevel = args.log_level or logging.DEBUG

        output_manager = output.OutputManager()

        output_manager.start_file_logging(debuglog, loglevel)

        urls = args.url.split()
        total_tests = len(urls)
        test_dir = data_dir.get_test_dir()
        output_manager.log_header("DEBUG LOG: %s" % debuglog)
        output_manager.log_header("TOTAL TESTS: %s" % total_tests)
        output_mapping = {'PASS': output_manager.log_pass,
                          'FAIL': output_manager.log_fail,
                          'TEST_NA': output_manager.log_skip,
                          'WARN': output_manager.log_warn}

        test_index = 1

        for url in urls:
            path_attempt = os.path.abspath(url)
            if os.path.exists(path_attempt):
                test_class = test.DropinTest
                test_instance = test_class(path=path_attempt, base_logdir=debugdir)
            else:
                test_module_dir = os.path.join(test_dir, url)
                f, p, d = imp.find_module(url, [test_module_dir])
                test_module = imp.load_module(url, f, p, d)
                f.close()
                test_class = getattr(test_module, url)
                test_instance = test_class(name=url, base_logdir=debugdir)

            sysinfo_logger = sysinfo.SysInfo(basedir=test_instance.sysinfodir)
            test_instance.start_logging()
            test_instance.setup()
            sysinfo_logger.start_job_hook()
            test_instance.run()
            test_instance.cleanup()
            test_instance.report()
            test_instance.stop_logging()

            output_func = output_mapping[test_instance.status]
            label = "(%s/%s) %s:" % (test_index, total_tests,
                                     test_instance.tagged_name)
            output_func(label, test_instance.time_elapsed)
            test_index += 1

        output_manager.stop_file_logging()
