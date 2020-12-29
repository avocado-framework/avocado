import os
import subprocess
import time

from ...utils import exit_codes
from .. import nrunner


class RequirementPackageRunner(nrunner.BaseRunner):
    """
    Runner for requirements of type package

    This runner handles, initially, the installation of packages using the
    avocado-software-manager. It can be easily extended to support other
    arguments, like `remove`.

    The arguments represent the packages that should be installed.
    """

    def run(self):
        env = self.runnable.kwargs or None
        if env and 'PATH' not in env:
            env['PATH'] = os.environ.get('PATH')
        process = subprocess.Popen(
            ['avocado-software-manager', 'install'] + list(self.runnable.args),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env)

        yield self.prepare_status('started')
        while process.poll() is None:
            time.sleep(nrunner.RUNNER_RUN_STATUS_INTERVAL)
            yield self.prepare_status('running')

        result = 'pass'
        if process.returncode == exit_codes.UTILITY_FAIL:
            result = 'error'

        yield self.prepare_status('finished',
                                  {'result': result,
                                   'returncode': process.returncode,
                                   'stdout': process.stdout.read(),
                                   'stderr': process.stderr.read()})


class RunnerApp(nrunner.BaseRunnerApp):
    PROG_NAME = 'avocado-runner-requirement-package'
    PROG_DESCRIPTION = ('nrunner application for requirements of type package')
    RUNNABLE_KINDS_CAPABLE = {'requirement-package': RequirementPackageRunner}


def main():
    nrunner.main(RunnerApp)


if __name__ == '__main__':
    main()
