# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# This code was inspired in the autotest project,
# client/shared/test.py
# Authors: Martin J Bligh <mbligh@google.com>,
#          Andy Whitcroft <apw@shadowen.org>

"""
Contains the base test implementation, used as a base for the actual
framework tests.
"""

import asyncio
import functools
import inspect
import os
import shutil
import sys
import tempfile
import time
import unittest
import warnings

from avocado.core import exceptions, parameters
from avocado.core.output import LOG_JOB
from avocado.core.settings import settings
from avocado.core.test_id import TestID
from avocado.core.version import VERSION
from avocado.utils import asset, astring, data_structures, genio
from avocado.utils import path as utils_path
from avocado.utils import stacktrace

#: Environment variable used to store the location of a temporary
#: directory which is preserved across all tests execution (usually in
#: one job)
COMMON_TMPDIR_NAME = 'AVOCADO_TESTS_COMMON_TMPDIR'

#: The list of test attributes that are used as the test state, which
#: is given to the test runner via the queue they share
TEST_STATE_ATTRIBUTES = ('name', 'logdir', 'logfile',
                         'status', 'running', 'paused',
                         'time_start', 'time_elapsed', 'time_end',
                         'actual_time_start', 'actual_time_end',
                         'fail_reason', 'fail_class', 'traceback',
                         'tags', 'timeout', 'whiteboard', 'phase')


class TestData:

    """
    Class that adds the ability for tests to have access to data files

    Writers of new test types can change the completely change the behavior
    and still be compatible by providing an :attr:`DATA_SOURCES` attribute
    and a meth:`get_data` method.
    """

    #: Defines the name of data sources that this implementation makes
    #: available.  Users may choose to pick data file from a specific
    #: source.
    DATA_SOURCES = ["variant", "test", "file"]

    def __init__(self):
        # Maximal allowed file name length is 255
        file_datadir = None
        if (self.filename is not None and
                len(os.path.basename(self.filename)) < 251):
            file_datadir = self.filename + '.data'
        self._data_sources_mapping = {
            "variant": [lambda: file_datadir,
                        lambda: (f"{self.__class__.__name__}."
                                 f"{self._testMethodName}"),
                        lambda: self.name.variant],
            "test": [lambda: file_datadir,
                     lambda: (f"{self.__class__.__name__}."
                              f"{self._testMethodName}")],
            "file": [lambda: file_datadir]
        }

    def _check_valid_data_source(self, source):
        """
        Utility to check if user chose a specific data source

        :param source: either None for no specific selection or a source name
        :type source: None or str
        :raises: ValueError
        """
        if source is not None and source not in self.DATA_SOURCES:
            msg = 'Data file source requested (%s) is not one of: %s'
            msg %= (source, ', '.join(self.DATA_SOURCES))
            raise ValueError(msg)

    def _get_datadir(self, source):
        path_components = self._data_sources_mapping.get(source)
        if path_components is None:
            return

        # evaluate lazily, needed when the class changes its own
        # information such as its datadir
        path_components = [func() for func in path_components]
        if None in path_components:
            return

        # if path components are absolute paths, let's believe that
        # they have already been treated (such as the entries that
        # return the self.datadir).  If not, let's split the path
        # components so that they can be treated in the next loop
        split_path_components = []
        for path_component in path_components:
            if not os.path.isabs(path_component):
                split_path_components += path_component.split(os.path.sep)
            else:
                split_path_components.append(path_component)

        # now, make sure each individual path component can be represented
        # in the filesystem.  again, if it's an absolute path, do nothing
        paths = []
        for path in split_path_components:
            if os.path.isabs(path):
                paths.append(path)
            else:
                paths.append(astring.string_to_safe_path(path))

        return os.path.join(*paths)

    def get_data(self, filename, source=None, must_exist=True):
        """
        Retrieves the path to a given data file.

        This implementation looks for data file in one of the sources
        defined by the :attr:`DATA_SOURCES` attribute.

        :param filename: the name of the data file to be retrieved
        :type filename: str
        :param source: one of the defined data sources.  If not set,
                       all of the :attr:`DATA_SOURCES` will be attempted
                       in the order they are defined
        :type source: str
        :param must_exist: whether the existence of a file is checked for
        :type must_exist: bool
        :rtype: str or None
        """
        log_fmt = 'DATA (filename=%s) => %s (%s)'
        if source is None:
            sources = self.DATA_SOURCES
        else:
            self._check_valid_data_source(source)
            sources = [source]
        for attempt_source in sources:
            datadir = self._get_datadir(attempt_source)
            if datadir is not None:
                # avoid returning a slash after the data directory name
                # when a file was not requested (thus return the data
                # directory itself)
                if not filename:
                    path = datadir
                else:
                    path = os.path.join(datadir, filename)
                if not must_exist:
                    self.log.debug(log_fmt, filename, path,
                                   (f"assumed to be located at "
                                    f"{attempt_source} source dir"))
                    return path
                else:
                    if os.path.exists(path):
                        self.log.debug(log_fmt, filename, path,
                                       f"found at {attempt_source} source dir")
                        return path

        self.log.debug(log_fmt, filename, "NOT FOUND",
                       f"data sources: {', '.join(sources)}")


class Test(unittest.TestCase, TestData):

    """
    Base implementation for the test class.

    You'll inherit from this to write your own tests. Typically you'll want
    to implement setUp(), test*() and tearDown() methods on your own tests.
    """
    #: Arbitrary string which will be stored in `$logdir/whiteboard` location
    #: when the test finishes.
    whiteboard = ''
    #: (unix) time when the test started, monotonic (could be forced from test)
    time_start = -1
    #: (unix) time when the test finished, monotonic (could be forced from test)
    time_end = -1
    #: duration of the test execution (always recalculated from time_end -
    #: time_start
    time_elapsed = -1
    #: (unix) time when the test started, actual one to be shown to users
    actual_time_start = -1
    #: (unix) time when the test finished, actual one to be shown to users
    actual_time_end = -1
    #: Test timeout (the timeout from params takes precedence)
    timeout = None

    def __init__(self, methodName='test', name=None, params=None,
                 base_logdir=None, config=None, runner_queue=None, tags=None):
        """
        Initializes the test.

        :param methodName: Name of the main method to run. For the sake of
                           compatibility with the original unittest class,
                           you should not set this.
        :param name: Pretty name of the test name. For normal tests,
                     written with the avocado API, this should not be
                     set.  This is reserved for internal Avocado use,
                     such as when running random executables as tests.
        :type name: :class:`avocado.core.test.TestID`
        :param base_logdir: Directory where test logs should go. If None
                            provided a temporary directory will be created.
        :param config: the job configuration, usually set by command
                       line options and argument parsing
        :type config: dict
        """
        self.__phase = 'INIT'

        def record_and_warn(*args, **kwargs):
            """ Record call to this function and log warning """
            if not self.__log_warn_used:
                self.__log_warn_used = True
            return original_log_warn(*args, **kwargs)

        if name is not None:
            self.__name = name
        else:
            self.__name = TestID(0, self.__class__.__name__)

        self.__tags = tags

        self._config = config or settings.as_dict()

        self.__base_logdir = base_logdir
        self.__base_logdir_tmp = None
        if self.__base_logdir is None:
            prefix = 'avocado_test_'
            self.__base_logdir_tmp = tempfile.TemporaryDirectory(prefix=prefix)
            self.__base_logdir = self.__base_logdir_tmp.name

        self.__logfile = os.path.join(self.logdir, 'debug.log')

        self._stdout_file = os.path.join(self.logdir, 'stdout')
        self._stderr_file = os.path.join(self.logdir, 'stderr')
        self._output_file = os.path.join(self.logdir, 'output')
        self._logging_handlers = {}

        self.__outputdir = utils_path.init_dir(self.logdir, 'data')

        self.__log = LOG_JOB
        original_log_warn = self.log.warning
        self.__log_warn_used = False
        self.log.warn = self.log.warning = record_and_warn

        self.log.info('INIT %s', self.name)

        paths = ['/test/*']
        if params is None:
            params = []
        elif isinstance(params, tuple):
            params, paths = params[0], params[1]
        self.__params = parameters.AvocadoParams(params, paths,
                                                 self.__log.name)
        default_timeout = getattr(self, "timeout", None)
        self.timeout = self.params.get("timeout", default=default_timeout)

        self.__status = None
        self.__fail_reason = None
        self.__fail_class = None
        self.__traceback = None
        self.__skip_test = False

        # Are initialized lazily
        self.__cache_dirs = None
        self.__base_tmpdir = None
        self.__workdir = None

        self.__running = False
        self.paused = False
        self.paused_msg = ''

        self.__runner_queue = runner_queue

        self.log.debug("Test metadata:")
        if self.filename:
            self.log.debug("  filename: %s", self.filename)
        try:
            teststmpdir = self.teststmpdir
        except EnvironmentError:
            pass
        else:
            self.log.debug("  teststmpdir: %s", teststmpdir)

        unittest.TestCase.__init__(self, methodName=methodName)
        TestData.__init__(self)

    @property
    def _base_tmpdir(self):
        if self.__base_tmpdir is None:
            self.__base_tmpdir = tempfile.mkdtemp(prefix="tmp_dir",
                                                  dir=self.__base_logdir)
        return self.__base_tmpdir

    @property
    def name(self):
        """
        Returns the Test ID, which includes the test name

        :rtype: TestID
        """
        return self.__name

    @property
    def tags(self):
        """
        The tags associated with this test
        """
        return self.__tags

    @property
    def log(self):
        """
        The enhanced test log
        """
        return self.__log

    @property
    def logdir(self):
        """
        Path to this test's logging dir
        """
        return self.__base_logdir

    @property
    def logfile(self):
        """
        Path to this test's main `debug.log` file
        """
        return self.__logfile

    @property
    def outputdir(self):
        """
        Directory available to test writers to attach files to the results
        """
        return self.__outputdir

    @property
    def params(self):
        """
        Parameters of this test (AvocadoParam instance)
        """
        return self.__params

    @property
    def basedir(self):
        """
        The directory where this test (when backed by a file) is located at
        """
        if self.filename is not None:
            return os.path.dirname(self.filename)
        else:
            return None

    @property
    def filename(self):
        """
        Returns the name of the file (path) that holds the current test
        """
        try:
            possibly_compiled = inspect.getfile(self.__class__)
            if possibly_compiled.endswith('.pyc') or possibly_compiled.endswith('.pyo'):
                source = possibly_compiled[:-1]
            else:
                source = possibly_compiled
        except TypeError:
            return None

        if os.path.exists(source):
            return source
        else:
            return None

    @property
    def teststmpdir(self):
        """
        Returns the path of the temporary directory that will stay the
        same for all tests in a given Job.
        """
        env_var = COMMON_TMPDIR_NAME
        path = os.environ.get(env_var)
        if path is None:
            msg = f'Environment Variable {env_var} is not set.'
            raise EnvironmentError(msg)
        return path

    @property
    def workdir(self):
        """
        This property returns a writable directory that exists during
        the entire test execution, but will be cleaned up once the
        test finishes.

        It can be used on tasks such as decompressing source tarballs,
        building software, etc.
        """
        if self.__workdir is None:
            self.__workdir = os.path.join(self._base_tmpdir,
                                          self.name.str_filesystem)
            utils_path.init_dir(self.__workdir)
            self.log.debug("Test workdir initialized at: %s", self.__workdir)
        return self.__workdir

    @property
    def cache_dirs(self):
        """
        Returns a list of cache directories as set in config file.
        """
        if self.__cache_dirs is None:
            self.__cache_dirs = self._config.get('datadir.paths.cache_dirs')
        return self.__cache_dirs

    @property
    def runner_queue(self):
        """
        The communication channel between test and test runner
        """
        return self.__runner_queue

    def set_runner_queue(self, runner_queue):
        """
        Override the runner_queue
        """
        if self.__runner_queue is not None:
            raise RuntimeError(f"Overriding of runner_queue multiple times "
                               f"is not allowed -> old={self.__runner_queue} "
                               f"new={runner_queue}")
        self.__runner_queue = runner_queue

    @property
    def status(self):
        """
        The result status of this test
        """
        return self.__status

    @property
    def running(self):
        """
        Whether this test is currently being executed
        """
        return self.__running

    @property
    def fail_reason(self):
        return self.__fail_reason

    @property
    def fail_class(self):
        return self.__fail_class

    @property
    def traceback(self):
        return self.__traceback

    @property
    def phase(self):
        """
        The current phase of the test execution

        Possible (string) values are: INIT, SETUP, TEST, TEARDOWN and FINISHED
        """
        return self.__phase

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return f"Test({self.name!r})"

    def _tag_start(self):
        self.log.info('START %s', self.name)
        self.__running = True
        self.time_start = time.monotonic()
        self.actual_time_start = time.time()

    def _tag_end(self):
        self.__running = False
        self.time_end = time.monotonic()
        self.actual_time_end = time.time()
        # for consistency sake, always use the same stupid method
        self._update_time_elapsed(self.time_end)

    def _update_time_elapsed(self, current_time=None):
        if current_time is None:
            current_time = time.monotonic()
        self.time_elapsed = current_time - self.time_start

    def report_state(self):
        """
        Send the current test state to the test runner process
        """
        if self.runner_queue is not None:
            self.runner_queue.put(self.get_state())

    def get_state(self):
        """
        Serialize selected attributes representing the test state

        :returns: a dictionary containing relevant test state data
        :rtype: dict
        """
        if self.running and self.time_start:
            self._update_time_elapsed()
        state = {key: getattr(self, key, None) for (key) in TEST_STATE_ATTRIBUTES}
        state['class_name'] = self.__class__.__name__
        state['params'] = [(path, key, value)
                           for path, key, value
                           in self.__params.iteritems()]
        return state

    def _run_test(self):
        """
        Auxiliary method to run setup and test method.
        """
        self._tag_start()
        testMethod = getattr(self, self._testMethodName)
        skip_test_condition = getattr(testMethod, '__skip_test_condition__', False)
        skip_test_condition_negate = getattr(testMethod, '__skip_test_condition_negate__', False)
        if skip_test_condition:
            if callable(skip_test_condition):
                if skip_test_condition_negate:
                    self.__skip_test = not bool(skip_test_condition(self))
                else:
                    self.__skip_test = bool(skip_test_condition(self))
            else:
                if skip_test_condition_negate:
                    self.__skip_test = not bool(skip_test_condition)
                else:
                    self.__skip_test = bool(skip_test_condition)
        else:
            self.__skip_test = bool(skip_test_condition)
        try:
            if self.__skip_test is False:
                self.__phase = 'SETUP'
                self.setUp()
        except exceptions.TestSkipError as details:
            self.__skip_test = True
            stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
            raise exceptions.TestSkipError(details)
        except exceptions.TestCancel:
            stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
            raise
        except:  # Old-style exceptions are not inherited from Exception()
            stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
            details = sys.exc_info()[1]
            raise exceptions.TestSetupFail(details)
        else:
            try:
                self.__phase = 'TEST'
                if inspect.iscoroutinefunction(testMethod):
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(testMethod())
                else:
                    testMethod()
            except exceptions.TestCancel:
                stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
                raise
            except:  # Old-style exceptions are not inherited from Exception() pylint: disable=W0702
                stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
                details = sys.exc_info()[1]
                if not isinstance(details, Exception):  # Avoid passing nasty exc
                    details = exceptions.TestError(f"{details!r}: {details}")
                self.log.debug("Local variables:")
                local_vars = inspect.trace()[1][0].f_locals
                for key, value in local_vars.items():
                    self.log.debug(' -> %s %s: %s', key, type(value), value)
                raise details

        self.__status = 'PASS'

    def _tearDown(self):
        """
        Auxiliary method to run tearDown.
        """
        try:
            if self.__skip_test is False:
                self.__phase = 'TEARDOWN'
                self.tearDown()
        except exceptions.TestSkipError as details:
            stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
            skip_illegal_msg = (f'Using skip decorators in tearDown() '
                                f'is not allowed in '
                                f'avocado, you must fix your '
                                f'test. Original skip exception: {details}')
            raise exceptions.TestError(skip_illegal_msg)
        except exceptions.TestCancel:
            stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
            raise
        except:  # avoid old-style exception failures pylint: disable=W0702
            stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
            details = sys.exc_info()[1]
            raise exceptions.TestSetupFail(details)

    def _setup_environment_variables(self):
        os.environ['AVOCADO_VERSION'] = VERSION
        if self.basedir is not None:
            os.environ['AVOCADO_TEST_BASEDIR'] = self.basedir
        if self.__workdir is not None:
            os.environ['AVOCADO_TEST_WORKDIR'] = self.workdir
        os.environ['AVOCADO_TEST_LOGDIR'] = self.logdir
        os.environ['AVOCADO_TEST_LOGFILE'] = self.logfile
        os.environ['AVOCADO_TEST_OUTPUTDIR'] = self.outputdir

    def _catch_test_status(self, method):
        """Wrapper around test methods for catching and logging failures."""
        try:
            method()
            if self.__log_warn_used:
                raise exceptions.TestWarn("Test passed but there were warnings "
                                          "during execution. Check the log for "
                                          "details.")
        except exceptions.TestBaseException as detail:
            self.__status = detail.status
            self.__fail_class = detail.__class__.__name__
            self.__fail_reason = astring.to_text(detail)
            self.__traceback = stacktrace.prepare_exc_info(sys.exc_info())
        except AssertionError as detail:
            self.__status = 'FAIL'
            self.__fail_class = detail.__class__.__name__
            self.__fail_reason = astring.to_text(detail)
            self.__traceback = stacktrace.prepare_exc_info(sys.exc_info())
        except Exception as detail:  # pylint: disable=W0703
            self.__status = 'ERROR'
            tb_info = stacktrace.tb_info(sys.exc_info())
            self.__traceback = stacktrace.prepare_exc_info(sys.exc_info())
            try:
                self.__fail_class = astring.to_text(detail.__class__.__name__)
                self.__fail_reason = astring.to_text(detail)
            except TypeError:
                self.__fail_class = "Exception"
                self.__fail_reason = ("Unable to get exception, check the "
                                      "traceback for details.")
            for e_line in tb_info:
                self.log.error(e_line)

    def run_avocado(self):
        """
        Wraps the run method, for execution inside the avocado runner.

        :result: Unused param, compatibility with :class:`unittest.TestCase`.
        """
        self._setup_environment_variables()
        self._catch_test_status(self._run_test)
        self._catch_test_status(self._tearDown)
        whiteboard_file = os.path.join(self.logdir, 'whiteboard')
        genio.write_file(whiteboard_file, self.whiteboard)
        self.__phase = 'FINISHED'
        self._tag_end()
        self._report()
        self.log.info("")

    def _report(self):
        """
        Report result to the logging system.
        """
        if self.fail_reason is not None:
            self.log.error("%s %s -> %s: %s", self.status,
                           self.name,
                           self.fail_class,
                           self.fail_reason)

        else:
            if self.status is None:
                self.__status = 'INTERRUPTED'
            self.log.info("%s %s", self.status,
                          self.name)

    def _deprecate_params_message(func):  # pylint: disable=E0213
        """ This decorator helps to deprecate parameter 'message' and
        replace it with 'msg'.
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            msg = None
            message = None

            if 'msg' in kwargs:
                msg = kwargs.get('msg')
            elif args:
                msg = args[0]

            if 'message' in kwargs:
                message = kwargs.get('message')
                if msg:
                    warnings.warn("Please favor parameter 'msg' and do not use "
                                  "it with the parameter 'message'",
                                  DeprecationWarning)

                else:
                    warnings.warn("The parameter 'message' has been deprecated."
                                  " Please use 'msg' instead", DeprecationWarning)

            actual_message = msg or message
            return func(actual_message)
        return wrapper

    @staticmethod
    @_deprecate_params_message
    def fail(msg=None):
        """
        Fails the currently running test.

        After calling this method a test will be terminated and have its status
        as FAIL.

        :param msg: an optional message that will be recorded in the logs
        :type msg: str
        """
        raise exceptions.TestFail(msg)

    @staticmethod
    @_deprecate_params_message
    def error(msg=None):
        """
        Errors the currently running test.

        After calling this method a test will be terminated and have its status
        as ERROR.

        :param msg: an optional message that will be recorded in the logs
        :type msg: str
        """
        raise exceptions.TestError(msg)

    @staticmethod
    @_deprecate_params_message
    def cancel(msg=None):
        """
        Cancels the test.

        This method is expected to be called from the test method, not
        anywhere else, since by definition, we can only cancel a test that
        is currently under execution. If you call this method outside the
        test method, avocado will mark your test status as ERROR, and
        instruct you to fix your test in the error message.

        :param msg: an optional message that will be recorded in the logs
        :type msg: str
        """
        raise exceptions.TestCancel(msg)

    def fetch_asset(self, name, asset_hash=None, algorithm=None,
                    locations=None, expire=None, find_only=False,
                    cancel_on_missing=False):
        """
        Method o call the utils.asset in order to fetch and asset file
        supporting hash check, caching and multiple locations.

        :param name: the asset filename or URL
        :param asset_hash: asset hash (optional)
        :param algorithm: hash algorithm (optional, defaults to
                          :data:`avocado.utils.asset.DEFAULT_HASH_ALGORITHM`)
        :param locations: list of URLs from where the asset can be
                          fetched (optional)
        :param expire: time for the asset to expire
        :param find_only: When `True`, `fetch_asset` only looks for the asset
                          in the cache, avoiding the download/move action.
                          Defaults to `False`.
        :param cancel_on_missing: whether the test should be canceled if the
                                  asset was not found in the cache or if
                                  `fetch` could not add the asset to the cache.
                                  Defaults to `False`.
        :raises OSError: when it fails to fetch the asset or file is not in
                         the cache and `cancel_on_missing` is `False`.
        :returns: asset file local path.
        """
        if expire is not None:
            expire = data_structures.time_to_seconds(str(expire))

        # If name has no protocol or network locations, attempt to find
        # the asset "by name" first. This is valid use case when the
        # asset has been previously put into any of the cache
        # directories, either manually or by the caching process
        # itself.
        parsed_name = asset.Asset.parse_name(name)
        if not (parsed_name.scheme or locations):
            try:
                return asset.Asset.get_asset_by_name(name,
                                                     self.cache_dirs,
                                                     expire,
                                                     asset_hash)
            except OSError as e:
                if cancel_on_missing:
                    self.cancel(f"Missing asset {name}")
                raise e

        asset_obj = asset.Asset(name, asset_hash, algorithm, locations,
                                self.cache_dirs, expire)

        try:
            # return the path to the asset when it was found or fetched
            if find_only:
                return asset_obj.find_asset_file()
            else:
                return asset_obj.fetch()
        except OSError as e:
            # if asset is not in the cache or there was a problem fetching
            # the asset
            if cancel_on_missing:
                # cancel when requested
                self.cancel(f"Missing asset {name}")
            # otherwise re-throw OSError
            raise e

    def _cleanup(self):
        if self.__base_logdir_tmp is not None:
            self.__base_logdir_tmp.cleanup()
            self.__base_logdir_tmp = None
        if self.__base_tmpdir is not None:
            if not self._config.get('run.keep_tmp') and os.path.exists(
                    self.__base_tmpdir):
                shutil.rmtree(self.__base_tmpdir)

    def tearDown(self):
        self._cleanup()

    def __del__(self):
        self._cleanup()
