import io
import multiprocessing
import os
import sys
import time
from unittest import TestLoader, TextTestRunner

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import (RUNNER_RUN_CHECK_INTERVAL,
                                         RUNNER_RUN_STATUS_INTERVAL,
                                         BaseRunner)


class PythonUnittestRunner(BaseRunner):
    """
    Runner for Python unittests

    The runnable uri is used as the test name that the native unittest
    TestLoader will use to find the test.  A native unittest test
    runner (TextTestRunner) will be used to execute the test.

    Runnable attributes usage:

     * uri: a single test reference, that is "a test method within a test case
            class" within a test module.  Example is:
            "./tests/foo.py:ClassFoo.test_bar".

     * args: not used

     * kwargs: not used
    """

    name = 'python-unittest'
    description = 'Runner for Python unittests'

    @property
    def unittest(self):
        """Returns the unittest part of an uri as tuple.

        Ex:

        uri = './avocado.dev/selftests/.data/unittests/test.py:Class.test_foo'
        It will return ("test", "Class", "test_foo")
        """

        uri = self.runnable.uri or ''
        if ':' in uri:
            module, class_method = uri.rsplit(':', 1)
        else:
            return None

        if module.endswith('.py'):
            module = module[:-3]
        module = module.rsplit(os.path.sep, 1)[-1]

        klass, method = class_method.rsplit('.', maxsplit=1)
        return module, klass, method

    @property
    def module_path(self):
        """Path where the module is located.

        Ex:
        uri = './avocado.dev/selftests/.data/unittests/test.py:Class.test_foo'
        It will return './avocado.dev/selftests/.data/unittests/'
        """
        uri = self.runnable.uri
        if not uri:
            return None
        module_path = uri.rsplit(':', 1)[0]
        return os.path.dirname(module_path)

    @property
    def module_class_method(self):
        """Return a dotted name with module + class + method.

        Important to note here that module is only the module file without the
        full path.
        """
        unittest = self.unittest
        if not unittest:
            return None

        return ".".join(unittest)

    @classmethod
    def _run_unittest(cls, module_path, module_class_method, queue):
        sys.path.insert(0, module_path)
        stream = io.StringIO()

        try:
            loader = TestLoader()
            suite = loader.loadTestsFromName(module_class_method)
        except ValueError as ex:
            msg = "loadTestsFromName error finding unittest {}: {}"
            queue.put({'status': 'finished',
                       'result': 'error',
                       'output': msg.format(module_class_method, str(ex))})
            return

        runner = TextTestRunner(stream=stream, verbosity=0)
        unittest_result = runner.run(suite)

        unittest_result_entries = None
        if len(unittest_result.errors) > 0:
            result = 'error'
            unittest_result_entries = unittest_result.errors
        elif len(unittest_result.failures) > 0:
            result = 'fail'
            unittest_result_entries = unittest_result.failures
        elif len(unittest_result.skipped) > 0:
            result = 'skip'
            unittest_result_entries = unittest_result.skipped
        else:
            result = 'pass'

        stream.seek(0)
        output = {'status': 'finished',
                  'result': result,
                  'output': stream.read()}

        if unittest_result_entries is not None:
            last_entry = unittest_result_entries[-1]
            lines = last_entry[1].splitlines()
            fail_reason = lines[-1]
            output['fail_reason'] = fail_reason

        stream.close()
        queue.put(output)

    def run(self, runnable):
        # pylint: disable=W0201
        self.runnable = runnable

        if not self.module_class_method:
            error_msg = ("Invalid URI: could not be converted to an unittest "
                         "dotted name.")
            yield self.prepare_status('finished', {'result': 'error',
                                                   'output': error_msg})
            return

        queue = multiprocessing.SimpleQueue()
        process = multiprocessing.Process(target=self._run_unittest,
                                          args=(self.module_path,
                                                self.module_class_method,
                                                queue))
        process.start()
        yield self.prepare_status('started')

        most_current_execution_state_time = None
        while queue.empty():
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)
            now = time.monotonic()
            if most_current_execution_state_time is not None:
                next_execution_state_mark = (most_current_execution_state_time +
                                             RUNNER_RUN_STATUS_INTERVAL)
            if (most_current_execution_state_time is None or
                    now > next_execution_state_mark):
                most_current_execution_state_time = now
                yield self.prepare_status('running')

        status = queue.get()
        yield self.prepare_status('running',
                                  {'type': 'stdout',
                                   'log': status.pop('output').encode()})
        status['time'] = time.monotonic()
        yield status


class RunnerApp(BaseRunnerApp):
    PROG_NAME = 'avocado-runner-python-unittest'
    PROG_DESCRIPTION = 'nrunner application for python-unittest tests'
    RUNNABLE_KINDS_CAPABLE = ['python-unittest']


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == '__main__':
    main()
