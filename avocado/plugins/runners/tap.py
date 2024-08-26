import io
import multiprocessing
import sys

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.tapparser import TapParser, TestResult
from avocado.core.utils.messages import FinishedMessage
from avocado.plugins.runners.exec_test import ExecTestRunner


class TAPRunner(ExecTestRunner):
    """Runner for standalone executables treated as TAP

    When creating the Runnable, use the following attributes:

     * kind: should be 'tap';

     * uri: path to a binary to be executed as another process. This must
       provides a TAP output.

     * args: any runnable argument will be given on the command line to the
       binary given by path

     * kwargs: you can specify multiple key=val as kwargs. This will be used as
       environment variables to the process.

    Example:

       runnable = Runnable(kind='tap',
                           uri='tests/foo.sh',
                           'bar', # arg 1
                           DEBUG='false') # kwargs 1 (environment)
    """

    name = "tap"
    description = "Runner for standalone executables treated as TAP"

    @staticmethod
    def _get_tap_result(stdout):
        parser = TapParser(io.StringIO(stdout.decode()))
        result = ""
        fail_reason = None
        for event in parser.parse():
            if isinstance(event, TapParser.Bailout):
                result = "error"
                break
            elif isinstance(event, TapParser.Error):
                result = "error"
                fail_reason = f"Tap format error: {event.message}"
                break
            elif isinstance(event, TapParser.Plan):
                if event.skipped:
                    if not result:
                        result = "skip"
                    continue
            elif isinstance(event, TapParser.Test):
                if event.result == TestResult.FAIL:
                    result = "fail"
                    fail_reason = event.explanation
                    break
                elif event.result == TestResult.SKIP:
                    if not result:
                        result = "skip"
                    continue
                elif event.result == TestResult.XPASS:
                    result = "warn"
                    if event.name:
                        tap_test_id = f"{event.number} ({event.name})"
                    else:
                        tap_test_id = f"{event.number}"
                    fail_reason = f"TODO test {tap_test_id} unexpectedly passed."
                    break
                else:
                    result = "pass"
        return result, fail_reason

    def _process_final_status(
        self, process, runnable, stdout=None, stderr=None
    ):  # pylint: disable=W0613
        result, fail_reason = self._get_tap_result(stdout)
        return FinishedMessage.get(result, fail_reason, returncode=process.returncode)


class RunnerApp(BaseRunnerApp):
    PROG_NAME = "avocado-runner-tap"
    PROG_DESCRIPTION = "nrunner application for executable tests that produce TAP"
    RUNNABLE_KINDS_CAPABLE = ["tap"]


def main():
    if sys.platform == "darwin":
        multiprocessing.set_start_method("fork")
    app = RunnerApp(print)
    app.run()


if __name__ == "__main__":
    main()
