import io
import multiprocessing
import os
import sys
import traceback
from unittest import TestLoader, TextTestRunner

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import PythonBaseRunner
from avocado.core.utils import messages


class PythonUnittestRunner(PythonBaseRunner):
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

    name = "python-unittest"
    description = "Runner for Python unittests"

    @property
    def unittest(self):
        """Returns the unittest part of an uri as tuple.

        Ex:

        uri = './avocado.dev/selftests/.data/unittests/test.py:Class.test_foo'
        It will return ("test", "Class", "test_foo")
        """

        uri = self.runnable.uri or ""
        if ":" in uri:
            module, class_method = uri.rsplit(":", 1)
        else:
            return None

        if module.endswith(".py"):
            module = module[:-3]
        module = module.rsplit(os.path.sep, 1)[-1]

        klass, method = class_method.rsplit(".", maxsplit=1)
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
        module_path = uri.rsplit(":", 1)[0]
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

    def _run(self, runnable, queue):
        def run_and_load_test():
            sys.path.insert(0, self.module_path)
            try:
                loader = TestLoader()
                suite = loader.loadTestsFromName(self.module_class_method)
            except ValueError as ex:
                msg = "loadTestsFromName error finding unittest {}: {}"
                queue.put(messages.StderrMessage.get(traceback.format_exc()))
                queue.put(
                    messages.FinishedMessage.get(
                        "error",
                        fail_reason=msg.format(self.module_class_method, str(ex)),
                        fail_class=ex.__class__.__name__,
                        traceback=traceback.format_exc(),
                    )
                )
                return None
            return runner.run(suite)

        # pylint: disable=W0201
        self.runnable = runnable

        if not self.module_class_method:
            queue.put(
                messages.StderrMessage.get(
                    "Invalid URI: could not be converted to an unittest dotted name."
                )
            )
            queue.put(
                messages.FinishedMessage.get(
                    "error",
                    fail_reason="Invalid URI: could not be converted to an unittest dotted name.",
                    fail_class=ValueError.__class__.__name__,
                    traceback=traceback.format_exc(),
                )
            )
            return None

        stream = io.StringIO()
        runner = TextTestRunner(stream=stream, verbosity=0)

        # running the actual test
        if "COVERAGE_RUN" in os.environ:
            from coverage import Coverage

            coverage = Coverage(data_suffix=True)
            with coverage.collect():
                unittest_result = run_and_load_test()
            coverage.save()
        else:
            unittest_result = run_and_load_test()

        if not unittest_result:
            return None

        unittest_result_entries = None
        if len(unittest_result.errors) > 0:
            result = "error"
            unittest_result_entries = unittest_result.errors
        elif len(unittest_result.failures) > 0:
            result = "fail"
            unittest_result_entries = unittest_result.failures
        elif len(unittest_result.skipped) > 0:
            result = "skip"
            unittest_result_entries = unittest_result.skipped
        else:
            result = "pass"

        stream.seek(0)
        queue.put(messages.StdoutMessage.get(stream.read()))
        fail_reason = None
        if unittest_result_entries is not None:
            last_entry = unittest_result_entries[-1]
            lines = last_entry[1].splitlines()
            fail_reason = lines[-1]

        stream.close()
        queue.put(messages.FinishedMessage.get(result, fail_reason=fail_reason))


class RunnerApp(BaseRunnerApp):
    PROG_NAME = "avocado-runner-python-unittest"
    PROG_DESCRIPTION = "nrunner application for python-unittest tests"
    RUNNABLE_KINDS_CAPABLE = ["python-unittest"]


def main():
    if sys.platform == "darwin":
        multiprocessing.set_start_method("fork")
    app = RunnerApp(print)
    app.run()


if __name__ == "__main__":
    main()
