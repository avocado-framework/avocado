import io
import subprocess
import time

from . import nrunner
from .tapparser import TapParser
from .tapparser import TestResult


class TAPRunner(nrunner.BaseRunner):
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
    def run(self):
        env = self.runnable.kwargs or None
        process = subprocess.Popen(
            [self.runnable.uri] + list(self.runnable.args),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env)

        while process.poll() is None:
            time.sleep(nrunner.RUNNER_RUN_STATUS_INTERVAL)
            yield {'status': 'running',
                   'timestamp': time.time()}

        stdout = io.TextIOWrapper(process.stdout)
        parser = TapParser(stdout)
        status = 'error'
        for event in parser.parse():
            if isinstance(event, TapParser.Bailout):
                status = 'error'
                break
            elif isinstance(event, TapParser.Error):
                status = 'error'
                break
            elif isinstance(event, TapParser.Test):
                if event.result in (TestResult.XPASS, TestResult.FAIL):
                    status = 'fail'
                    break
                elif event.result == TestResult.SKIP:
                    status = 'skip'
                    break
                else:
                    status = 'pass'

        yield {'status': status,
               'returncode': process.returncode,
               'timestamp': time.time()}


class RunnerApp(nrunner.BaseRunnerApp):
    PROG_NAME = 'avocado-runner-tap'
    PROG_DESCRIPTION = ('*EXPERIMENTAL* N(ext) Runner for executable tests '
                        'that produce TAP')
    RUNNABLE_KINDS_CAPABLE = {'tap': TAPRunner}


def main():
    nrunner.main(RunnerApp)


if __name__ == '__main__':
    main()
