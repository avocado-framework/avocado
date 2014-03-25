"""
Class that describes a sequence of automated operations.
"""
import imp
import logging
import os
import time

from avocado.core import data_dir
from avocado.core import output
from avocado import test
from avocado import sysinfo

JOB_STATUSES = {"TEST_NA": False,
                "ABORT": False,
                "ERROR": False,
                "FAIL": False,
                "WARN": False,
                "PASS": True,
                "START": True,
                "ALERT": False,
                "RUNNING": False,
                "NOSTATUS": False}


class Job(object):

    """
    A Job is a set of operations performed on a test machine.

    Most of the time, we are interested in simply running tests,
    along with setup operations and event recording.
    """

    def __init__(self, args=None):
        self.args = args
        start_time = time.strftime('%Y-%m-%d-%H.%M.%S')
        if self.args is not None:
            logdir = args.logdir or data_dir.get_logs_dir()
        else:
            logdir = data_dir.get_logs_dir()
        debugbase = 'run-%s' % start_time
        self.debugdir = os.path.join(logdir, debugbase)
        if not os.path.isdir(self.debugdir):
            os.makedirs(self.debugdir)
        latestdir = os.path.join(logdir, "latest")
        try:
            os.unlink(latestdir)
        except OSError:
            pass
        os.symlink(debugbase, latestdir)

        self.debuglog = os.path.join(self.debugdir, "debug.log")
        if self.args is not None:
            self.loglevel = args.log_level or logging.DEBUG
        else:
            self.loglevel = logging.DEBUG
        self.test_dir = data_dir.get_test_dir()
        self.test_index = 1

        self.output_manager = output.OutputManager()

    def _load_test_instance(self, url):
        path_attempt = os.path.abspath(url)
        if os.path.exists(path_attempt):
            test_class = test.DropinTest
            test_instance = test_class(path=path_attempt,
                                       base_logdir=self.debugdir)
        else:
            test_module_dir = os.path.join(self.test_dir, url)
            f, p, d = imp.find_module(url, [test_module_dir])
            test_module = imp.load_module(url, f, p, d)
            f.close()
            test_class = getattr(test_module, url)
            test_instance = test_class(name=url, base_logdir=self.debugdir)
        return test_instance

    def _run_test_instance(self, test_instance):
        """
        Call the test instance methods in the right order.

        Along with the test methods, it also collects syinfo.

        :params test_instance: avocado.test.Test derived class instance.
        """
        sysinfo_logger = sysinfo.SysInfo(basedir=test_instance.sysinfodir)
        test_instance.start_logging()
        test_instance.setup()
        sysinfo_logger.start_job_hook()
        test_instance.run()
        test_instance.cleanup()
        test_instance.report()
        test_instance.stop_logging()
        return test_instance

    def run_test(self, url):
        """
        Run a single test URL.
        """
        test_instance = self._load_test_instance(url)
        self._run_test_instance(test_instance)
        return test_instance

    def run(self, urls=None):
        """
        Main job method. Runs a list of test URLs to its completion.
        """
        if urls is None:
            urls = self.args.url.split()

        total_tests = len(urls)
        self.output_manager.start_file_logging(self.debuglog, self.loglevel)
        self.output_manager.log_header("DEBUG LOG: %s" % self.debuglog)
        self.output_manager.log_header("TOTAL TESTS: %s" % total_tests)
        self.output_mapping = {'PASS': self.output_manager.log_pass,
                               'FAIL': self.output_manager.log_fail,
                               'TEST_NA': self.output_manager.log_skip,
                               'WARN': self.output_manager.log_warn}

        for url in urls:
            test_instance = self.run_test(url)
            output_func = self.output_mapping[test_instance.status]
            label = "(%s/%s) %s:" % (self.test_index, total_tests,
                                     test_instance.tagged_name)
            output_func(label, test_instance.time_elapsed)
            self.test_index += 1

        self.output_manager.stop_file_logging()


class TestModuleRunner(object):

    """
    Convenience class to make avocado test modules executable.
    """

    def __init__(self, module='__main__'):
        if isinstance(module, basestring):
            self.module = __import__(module)
            for part in module.split('.')[1:]:
                self.module = getattr(self.module, part)
        else:
            self.module = module
        url = None
        for key, value in self.module.__dict__.iteritems():
            try:
                if issubclass(value, test.Test):
                    url = key
            except TypeError:
                pass
        self.job = Job()
        if url is not None:
            self.job.run(urls=[url])

main = TestModuleRunner
