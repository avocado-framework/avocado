import io
import os
import subprocess
import time

from . import nrunner
from .tapparser import TapParser, TestResult


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
        if env and 'PATH' not in env:
            env['PATH'] = os.environ.get('PATH')
        process = subprocess.Popen(
            [self.runnable.uri] + list(self.runnable.args),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env)

        while process.poll() is None:
            time.sleep(nrunner.RUNNER_RUN_STATUS_INTERVAL)
            yield self.prepare_status('running')

        stdout = process.stdout.read()
        parser = TapParser(io.StringIO(stdout.decode()))
        result = 'error'
        for event in parser.parse():
            if isinstance(event, TapParser.Bailout):
                result = 'error'
                break
            elif isinstance(event, TapParser.Error):
                result = 'error'
                break
            elif isinstance(event, TapParser.Test):
                if event.result in (TestResult.XPASS, TestResult.FAIL):
                    result = 'fail'
                    break
                elif event.result == TestResult.SKIP:
                    result = 'skip'
                    break
                else:
                    result = 'pass'

        yield self.prepare_status('finished',
                                  {'result': result,
                                   'returncode': process.returncode,
                                   'stdout': stdout,
                                   'stderr': process.stderr.read()})


class RunnerApp(nrunner.BaseRunnerApp):
    PROG_NAME = 'avocado-runner-tap'
    PROG_DESCRIPTION = ('nrunner application for executable tests that '
                        'produce TAP')
    RUNNABLE_KINDS_CAPABLE = {'tap': TAPRunner}


def main():
    nrunner.main(RunnerApp)


if __name__ == '__main__':
    main()
