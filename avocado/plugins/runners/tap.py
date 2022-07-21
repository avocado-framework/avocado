import io

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
        result = "error"
        for event in parser.parse():
            if isinstance(event, TapParser.Bailout):
                result = "error"
                break
            elif isinstance(event, TapParser.Error):
                result = "error"
                break
            elif isinstance(event, TapParser.Plan):
                if event.skipped:
                    result = "skip"
                    break
            elif isinstance(event, TapParser.Test):
                if event.result in (TestResult.XPASS, TestResult.FAIL):
                    result = "fail"
                    break
                elif event.result == TestResult.SKIP:
                    result = "skip"
                    break
                else:
                    result = "pass"
        return result

    def _process_final_status(
        self, process, runnable, stdout=None, stderr=None
    ):  # pylint: disable=W0613
        return FinishedMessage.get(
            self._get_tap_result(stdout), returncode=process.returncode
        )


class RunnerApp(BaseRunnerApp):
    PROG_NAME = "avocado-runner-tap"
    PROG_DESCRIPTION = "nrunner application for executable tests that produce TAP"
    RUNNABLE_KINDS_CAPABLE = ["tap"]


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == "__main__":
    main()
