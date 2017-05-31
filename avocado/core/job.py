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
# Copyright: Red Hat Inc. 2013-2015
# Authors: Lucas Meneghel Rodrigues <lmr@redhat.com>
#          Ruda Moura <rmoura@redhat.com>

"""
Job module - describes a sequence of automated test operations.
"""

import argparse
import logging
import os
import re
import shutil
import sys
import tempfile
import time
import traceback

from . import version
from . import data_dir
from . import dispatcher
from . import runner
from . import loader
from . import sysinfo
from . import result
from . import exit_codes
from . import exceptions
from . import job_id
from . import output
from . import varianter
from . import test
from . import jobdata
from .output import STD_OUTPUT
from .settings import settings
from ..utils import astring
from ..utils import path
from ..utils import runtime
from ..utils import stacktrace
from ..utils import data_structures
from ..utils import process
from .output import LOG_JOB
from .output import LOG_UI


_NEW_ISSUE_LINK = 'https://github.com/avocado-framework/avocado/issues/new'


class Job(object):

    """
    A Job is a set of operations performed on a test machine.

    Most of the time, we are interested in simply running tests,
    along with setup operations and event recording.
    """

    def __init__(self, args=None):
        """
        Creates an instance of Job class.

        :param args: an instance of :class:`argparse.Namespace`.
        """
        if args is None:
            args = argparse.Namespace()
        self.args = args
        self.references = getattr(args, "reference", [])
        self.log = LOG_UI
        self.standalone = getattr(self.args, 'standalone', False)
        if getattr(self.args, "dry_run", False):  # Modify args for dry-run
            if not self.args.unique_job_id:
                self.args.unique_job_id = "0" * 40
            self.args.sysinfo = False
            if self.args.logdir is None:
                self.args.logdir = tempfile.mkdtemp(prefix="avocado-dry-run-")

        unique_id = getattr(self.args, 'unique_job_id', None)
        if unique_id is None:
            unique_id = job_id.create_unique_job_id()
        self.unique_id = unique_id
        #: The log directory for this job, also known as the job results
        #: directory.  If it's set to None, it means that the job results
        #: directory has not yet been created.
        self.logdir = None
        self._setup_job_results()
        raw_log_level = settings.get_value('job.output', 'loglevel',
                                           default='debug')
        mapping = {'info': logging.INFO,
                   'debug': logging.DEBUG,
                   'warning': logging.WARNING,
                   'error': logging.ERROR,
                   'critical': logging.CRITICAL}
        if raw_log_level in mapping:
            self.loglevel = mapping[raw_log_level]
        else:
            self.loglevel = logging.DEBUG

        self.status = "RUNNING"
        self.result = result.Result(self)
        self.sysinfo = None
        self.timeout = getattr(self.args, 'job_timeout', 0)
        #: The time at which the job has started or `-1` if it has not been
        #: started by means of the `run()` method.
        self.time_start = -1
        #: The time at which the job has finished or `-1` if it has not been
        #: started by means of the `run()` method.
        self.time_end = -1
        #: The total amount of time the job took from start to finish,
        #: or `-1` if it has not been started by means of the `run()` method
        self.time_elapsed = -1
        self.__logging_handlers = {}
        self.__start_job_logging()
        self.funcatexit = data_structures.CallbackRegister("JobExit %s"
                                                           % self.unique_id,
                                                           LOG_JOB)
        self._stdout_stderr = None
        self.replay_sourcejob = getattr(self.args, 'replay_sourcejob', None)
        self.exitcode = exit_codes.AVOCADO_ALL_OK
        #: The list of discovered/resolved tests that will be attempted to
        #: be run by this job.  If set to None, it means that test resolution
        #: has not been attempted.  If set to an empty list, it means that no
        #: test was found during resolution.
        self.test_suite = None

        # The result events dispatcher is shared with the test runner.
        # Because of our goal to support using the phases of a job
        # freely, let's get the result events dispatcher ready early.
        # A future optimization may load it on demand.
        self._result_events_dispatcher = dispatcher.ResultEventsDispatcher(self.args)
        output.log_plugin_failures(self._result_events_dispatcher.load_failures)

        # Checking whether we will keep the Job tmp_dir or not.
        # If yes, we set the basedir for a stable location.
        basedir = None
        keep_tmp = getattr(self.args, "keep_tmp", None)
        if keep_tmp == 'on':
            basedir = self.logdir
        # Calling get_tmp_dir() early as the basedir will be set
        # in the first call.
        data_dir.get_tmp_dir(basedir)

    def _setup_job_results(self):
        """
        Prepares a job result directory, also known as logdir, for this job
        """
        logdir = getattr(self.args, 'logdir', None)
        if self.standalone:
            if logdir is not None:
                logdir = os.path.abspath(logdir)
                self.logdir = data_dir.create_job_logs_dir(logdir=logdir,
                                                           unique_id=self.unique_id)
            else:
                self.logdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        else:
            if logdir is None:
                self.logdir = data_dir.create_job_logs_dir(unique_id=self.unique_id)
            else:
                logdir = os.path.abspath(logdir)
                self.logdir = data_dir.create_job_logs_dir(logdir=logdir,
                                                           unique_id=self.unique_id)
        if not (self.standalone or getattr(self.args, "dry_run", False)):
            self._update_latest_link()
        self.logfile = os.path.join(self.logdir, "job.log")
        idfile = os.path.join(self.logdir, "id")
        with open(idfile, 'w') as id_file_obj:
            id_file_obj.write("%s\n" % self.unique_id)
            id_file_obj.flush()
            os.fsync(id_file_obj)

    def __start_job_logging(self):
        # Enable test logger
        fmt = ('%(asctime)s %(module)-16.16s L%(lineno)-.4d %('
               'levelname)-5.5s| %(message)s')
        test_handler = output.add_log_handler(LOG_JOB,
                                              logging.FileHandler,
                                              self.logfile, self.loglevel, fmt)
        root_logger = logging.getLogger()
        root_logger.addHandler(test_handler)
        root_logger.setLevel(self.loglevel)
        self.__logging_handlers[test_handler] = [LOG_JOB.name, ""]
        # Add --store-logging-streams
        fmt = '%(asctime)s %(levelname)-5.5s| %(message)s'
        formatter = logging.Formatter(fmt=fmt, datefmt='%H:%M:%S')
        for name in getattr(self.args, "store_logging_stream", []):
            name = re.split(r'(?<!\\):', name, maxsplit=1)
            if len(name) == 1:
                name = name[0]
                level = logging.INFO
            else:
                level = (int(name[1]) if name[1].isdigit()
                         else logging.getLevelName(name[1].upper()))
                name = name[0]
            try:
                logfile = os.path.join(self.logdir, name + "." +
                                       logging.getLevelName(level))
                handler = output.add_log_handler(name, logging.FileHandler,
                                                 logfile, level, formatter)
            except ValueError as details:
                self.log.error("Failed to set log for --store-logging-stream "
                               "%s:%s: %s.", name, level, details)
            else:
                self.__logging_handlers[handler] = [name]
        # Enable console loggers
        enabled_logs = getattr(self.args, "show", [])
        if ('test' in enabled_logs and
                'early' not in enabled_logs):
            self._stdout_stderr = sys.stdout, sys.stderr
            # Enable std{out,err} but redirect booth to stderr
            sys.stdout = STD_OUTPUT.stdout
            sys.stderr = STD_OUTPUT.stdout
            test_handler = output.add_log_handler(LOG_JOB,
                                                  logging.StreamHandler,
                                                  STD_OUTPUT.stdout,
                                                  logging.DEBUG,
                                                  fmt="%(message)s")
            root_logger.addHandler(test_handler)
            self.__logging_handlers[test_handler] = [LOG_JOB.name, ""]

    def __stop_job_logging(self):
        if self._stdout_stderr:
            sys.stdout, sys.stderr = self._stdout_stderr
        for handler, loggers in self.__logging_handlers.iteritems():
            for logger in loggers:
                logging.getLogger(logger).removeHandler(handler)

    def _update_latest_link(self):
        """
        Update the latest job result symbolic link [avocado-logs-dir]/latest.
        """
        def soft_abort(msg):
            """ Only log the problem """
            LOG_JOB.warning("Unable to update the latest link: %s" % msg)
        basedir = os.path.dirname(self.logdir)
        basename = os.path.basename(self.logdir)
        proc_latest = os.path.join(basedir, "latest.%s" % os.getpid())
        latest = os.path.join(basedir, "latest")
        if os.path.exists(latest) and not os.path.islink(latest):
            soft_abort('"%s" already exists and is not a symlink' % latest)
            return

        if os.path.exists(proc_latest):
            try:
                os.unlink(proc_latest)
            except OSError as details:
                soft_abort("Unable to remove %s: %s" % (proc_latest, details))
                return

        try:
            os.symlink(basename, proc_latest)
            os.rename(proc_latest, latest)
        except OSError as details:
            soft_abort("Unable to create create latest symlink: %s" % details)
            return
        finally:
            if os.path.exists(proc_latest):
                os.unlink(proc_latest)

    def _start_sysinfo(self):
        if hasattr(self.args, 'sysinfo'):
            if self.args.sysinfo == 'on':
                sysinfo_dir = path.init_dir(self.logdir, 'sysinfo')
                self.sysinfo = sysinfo.SysInfo(basedir=sysinfo_dir)

    def _make_test_runner(self):
        if hasattr(self.args, 'test_runner'):
            test_runner_class = self.args.test_runner
        else:
            test_runner_class = runner.TestRunner

        self.test_runner = test_runner_class(job=self,
                                             result=self.result)

    def _make_test_suite(self, references=None):
        """
        Prepares a test suite to be used for running tests

        :param references: String with tests references to be resolved, and then
                           run, separated by whitespace. Optionally, a
                           list of tests (each test a string).
        :returns: a test suite (a list of test factories)
        """
        loader.loader.load_plugins(self.args)
        try:
            force = getattr(self.args, 'ignore_missing_references', 'off')
            suite = loader.loader.discover(references, force=force)
            if getattr(self.args, 'filter_by_tags', False):
                suite = loader.filter_test_tags(
                    suite,
                    self.args.filter_by_tags,
                    self.args.filter_by_tags_include_empty)
        except loader.LoaderUnhandledReferenceError as details:
            raise exceptions.OptionValidationError(details)
        except KeyboardInterrupt:
            raise exceptions.JobError('Command interrupted by user...')

        if not getattr(self.args, "dry_run", False):
            return suite
        for i in xrange(len(suite)):
            suite[i] = [test.DryRunTest, suite[i][1]]
        return suite

    def _log_job_id(self):
        LOG_JOB.info('Job ID: %s', self.unique_id)
        if self.replay_sourcejob is not None:
            LOG_JOB.info('Replay of Job ID: %s', self.replay_sourcejob)
        LOG_JOB.info('')

    @staticmethod
    def _log_cmdline():
        cmdline = " ".join(sys.argv)
        LOG_JOB.info("Command line: %s", cmdline)
        LOG_JOB.info('')

    @staticmethod
    def _log_avocado_version():
        LOG_JOB.info('Avocado version: %s', version.VERSION)
        if os.path.exists('.git') and os.path.exists('avocado.spec'):
            cmd = "git show --summary --pretty='%H'"
            result = process.run(cmd, ignore_status=True)
            status = result.exit_status
            top_commit = result.stdout.splitlines()[0]
            cmd2 = "git rev-parse --abbrev-ref HEAD"
            result2 = process.run(cmd2)
            status2 = result2.exit_status
            branch = result2.stdout
            # Let's display information only if git is installed
            # (commands succeed).
            if status == 0 and status2 == 0:
                LOG_JOB.info('Avocado git repo info')
                LOG_JOB.info("Top commit: %s", top_commit)
                LOG_JOB.info("Branch: %s", branch)
        LOG_JOB.info('')

    @staticmethod
    def _log_avocado_config():
        LOG_JOB.info('Config files read (in order):')
        for cfg_path in settings.config_paths:
            LOG_JOB.info(cfg_path)
        if settings.config_paths_failed:
            LOG_JOB.info('Config files failed to read (in order):')
            for cfg_path in settings.config_paths_failed:
                LOG_JOB.info(cfg_path)
        LOG_JOB.info('')

        LOG_JOB.info('Avocado config:')
        header = ('Section.Key', 'Value')
        config_matrix = []
        for section in settings.config.sections():
            for value in settings.config.items(section):
                config_key = ".".join((section, value[0]))
                config_matrix.append([config_key, value[1]])

        for line in astring.iter_tabular_output(config_matrix, header):
            LOG_JOB.info(line)
        LOG_JOB.info('')

    def _log_avocado_datadir(self):
        LOG_JOB.info('Avocado Data Directories:')
        LOG_JOB.info('')
        LOG_JOB.info('base     ' + data_dir.get_base_dir())
        LOG_JOB.info('tests    ' + data_dir.get_test_dir())
        LOG_JOB.info('data     ' + data_dir.get_data_dir())
        LOG_JOB.info('logs     ' + self.logdir)
        LOG_JOB.info('')

    def _log_variants(self, variants):
        lines = variants.to_str(summary=1, variants=1, use_utf8=False)
        for line in lines.splitlines():
            LOG_JOB.info(line)

    def _log_tmp_dir(self):
        LOG_JOB.info('Temporary dir: %s', data_dir.get_tmp_dir())
        LOG_JOB.info('')

    def _log_job_debug_info(self, mux):
        """
        Log relevant debug information to the job log.
        """
        self._log_cmdline()
        self._log_avocado_version()
        self._log_avocado_config()
        self._log_avocado_datadir()
        self._log_variants(mux)
        self._log_tmp_dir()
        self._log_job_id()

    def create_test_suite(self):
        """
        Creates the test suite for this Job

        This is a public Job API as part of the documented Job phases
        """
        try:
            self.test_suite = self._make_test_suite(self.references)
            self.result.tests_total = len(self.test_suite)
        except loader.LoaderError as details:
            stacktrace.log_exc_info(sys.exc_info(), LOG_UI.getChild("debug"))
            raise exceptions.OptionValidationError(details)

        if not self.test_suite:
            if self.references:
                references = " ".join(self.references)
                e_msg = ("No tests found for given test references, try "
                         "'avocado list -V %s' for details" % references)
            else:
                e_msg = ("No test references provided nor any other arguments "
                         "resolved into tests. Please double check the executed"
                         " command.")
            raise exceptions.OptionValidationError(e_msg)

    def pre_tests(self):
        """
        Run the pre tests execution hooks

        By default this runs the plugins that implement the
        :class:`avocado.core.plugin_interfaces.JobPreTests` interface.
        """
        self._result_events_dispatcher.map_method('pre_tests', self)

    def run_tests(self):
        variant = getattr(self.args, "avocado_variants", None)
        if variant is None:
            variant = varianter.Varianter()
        if not variant.is_parsed():   # Varianter not yet parsed, apply args
            try:
                variant.parse(self.args)
            except (IOError, ValueError) as details:
                raise exceptions.OptionValidationError("Unable to parse "
                                                       "variant: %s" % details)

        self._make_test_runner()
        self._start_sysinfo()

        self._log_job_debug_info(variant)
        jobdata.record(self.args, self.logdir, variant, self.references,
                       sys.argv)
        replay_map = getattr(self.args, 'replay_map', None)
        execution_order = getattr(self.args, "execution_order", None)
        summary = self.test_runner.run_suite(self.test_suite,
                                             variant,
                                             self.timeout,
                                             replay_map,
                                             execution_order)
        # If it's all good so far, set job status to 'PASS'
        if self.status == 'RUNNING':
            self.status = 'PASS'
        LOG_JOB.info('Test results available in %s', self.logdir)

        if summary is None:
            self.exitcode |= exit_codes.AVOCADO_JOB_FAIL
            return self.exitcode

        if 'INTERRUPTED' in summary:
            self.exitcode |= exit_codes.AVOCADO_JOB_INTERRUPTED
        if 'FAIL' in summary:
            self.exitcode |= exit_codes.AVOCADO_TESTS_FAIL

        return self.exitcode

    def post_tests(self):
        """
        Run the post tests execution hooks

        By default this runs the plugins that implement the
        :class:`avocado.core.plugin_interfaces.JobPostTests` interface.
        """
        self._result_events_dispatcher.map_method('post_tests', self)

    def run(self):
        """
        Runs all job phases, returning the test execution results.

        This method is supposed to be the simplified interface for
        jobs, that is, they run all phases of a job.

        :return: Integer with overall job status. See
                 :mod:`avocado.core.exit_codes` for more information.
        """
        if self.time_start == -1:
            self.time_start = time.time()
        runtime.CURRENT_JOB = self
        try:
            self.create_test_suite()
            self.pre_tests()
            return self.run_tests()
        except exceptions.JobBaseException as details:
            self.status = details.status
            fail_class = details.__class__.__name__
            self.log.error('\nAvocado job failed: %s: %s', fail_class, details)
            self.exitcode |= exit_codes.AVOCADO_JOB_FAIL
            return self.exitcode
        except exceptions.OptionValidationError as details:
            self.log.error('\n' + str(details))
            self.exitcode |= exit_codes.AVOCADO_JOB_FAIL
            return self.exitcode

        except Exception as details:
            self.status = "ERROR"
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_info = traceback.format_exception(exc_type, exc_value,
                                                 exc_traceback.tb_next)
            fail_class = details.__class__.__name__
            self.log.error('\nAvocado crashed: %s: %s', fail_class, details)
            for line in tb_info:
                self.log.debug(line)
            self.log.error("Please include the traceback info and command line"
                           " used on your bug report")
            self.log.error('Report bugs visiting %s', _NEW_ISSUE_LINK)
            self.exitcode |= exit_codes.AVOCADO_FAIL
            return self.exitcode
        finally:
            self.post_tests()
            if self.time_end == -1:
                self.time_end = time.time()
                self.time_elapsed = self.time_end - self.time_start
            self.__stop_job_logging()


class TestProgram(object):

    """
    Convenience class to make avocado test modules executable.
    """

    def __init__(self):
        # Avoid fork loop/bomb when running a test via avocado.main() that
        # calls avocado.main() itself
        if os.environ.get('AVOCADO_STANDALONE_IN_MAIN', False):
            sys.stderr.write('AVOCADO_STANDALONE_IN_MAIN environment variable '
                             'found. This means that this code is being '
                             'called recursively. Exiting to avoid an infinite'
                             ' fork loop.\n')
            sys.exit(exit_codes.AVOCADO_FAIL)
        os.environ['AVOCADO_STANDALONE_IN_MAIN'] = 'True'

        self.progName = os.path.basename(sys.argv[0])
        output.add_log_handler("", output.ProgressStreamHandler,
                               fmt="%(message)s")
        self.parseArgs(sys.argv[1:])
        self.args.reference = [sys.argv[0]]
        self.runTests()

    def parseArgs(self, argv):
        self.parser = argparse.ArgumentParser(prog=self.progName)
        self.parser.add_argument('-r', '--remove-test-results', action='store_true',
                                 help='remove all test results files after test execution')
        self.parser.add_argument('-d', '--test-results-dir', dest='logdir', default=None,
                                 metavar='TEST_RESULTS_DIR',
                                 help='use an alternative test results directory')
        self.args = self.parser.parse_args(argv)

    def runTests(self):
        self.args.standalone = True
        self.args.show = ["test"]
        output.reconfigure(self.args)
        self.job = Job(self.args)
        exit_status = self.job.run()
        if self.args.remove_test_results is True:
            shutil.rmtree(self.job.logdir)
        sys.exit(exit_status)


main = TestProgram
