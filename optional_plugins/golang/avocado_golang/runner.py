import subprocess
import time

from avocado_golang.golang import GO_BIN

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import RUNNER_RUN_STATUS_INTERVAL, BaseRunner
from avocado.core.utils import messages


class GolangRunner(BaseRunner):
    """Runner for Golang tests.

    When creating the Runnable, use the following attributes:

     * kind: should be 'golang';

     * uri: module name and optionally a test method name, separated by colon;

     * args: not used

     * kwargs: not used

    Example:

       runnable = Runnable(kind='golang',
                           uri='countavocados:ExampleContainers')
    """

    name = 'golang'
    description = 'Runner for Golang tests'

    def run(self, runnable):
        # pylint: disable=W0201
        self.runnable = runnable
        error_msgs = []
        if not GO_BIN:
            error_msgs.append('"go" binary is not available')

        if not self.runnable.uri:
            error_msgs.append("an empty URI was given")

        if error_msgs:
            yield self.prepare_status('finished',
                                      {'result': 'error',
                                       'output': "and , ".join(error_msgs)})
            return

        yield messages.StartedMessage.get()
        module_test = self.runnable.uri.split(':', 1)
        module = module_test[0]
        try:
            test = module_test[1]
        except IndexError:
            test = None

        cmd = [GO_BIN, 'test', '-v', module]
        if test is not None:
            cmd += ['-run', f'{test}$']

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        while process.poll() is None:
            time.sleep(RUNNER_RUN_STATUS_INTERVAL)
            yield messages.RunningMessage.get()

        result = 'pass' if process.returncode == 0 else 'fail'
        yield messages.StdoutMessage.get(process.stdout.read())
        yield messages.StderrMessage.get(process.stderr.read())
        yield messages.FinishedMessage.get(result,
                                           returncode=process.returncode)


class RunnerApp(BaseRunnerApp):
    PROG_NAME = 'avocado-runner-golang'
    PROG_DESCRIPTION = 'nrunner application for golang tests'
    RUNNABLE_KINDS_CAPABLE = ['golang']


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == '__main__':
    main()
