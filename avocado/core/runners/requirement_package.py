import subprocess
import time

from ...utils import exit_codes
from .. import nrunner


class RequirementPackageRunner(nrunner.BaseRunner):
    """Runner for requirements of type package

    This runner handles, the installation, verification and removal of
    packages using the avocado-software-manager.

    Runnable attributes usage:

     * kind: 'requirement-package'

     * uri: not used

     * args: not used one of 'install', 'check' or 'remove'

     * kwargs: supported kwargs by this runner:
                - name='package_name'
                - optional: action= one of 'install', 'check' or 'remove'
                  eg.: action=install, action=check, action=remove
                  when 'action' is not defined, action='install' is the default
    """

    def run(self):
        # check if there is a valid 'action' argument
        cmd = self.runnable.kwargs.get('action')
        if cmd not in ['install', 'check', 'remove']:
            # missing or invalid argument is translated to 'install'
            cmd = 'install'
        # use the correct check command on avocado-software-manager
        if cmd == 'check':
            cmd = 'check-installed'

        yield self.prepare_status('started')

        package = self.runnable.kwargs.get('name')
        # if package was passed correctly, run avocado-software-manager
        if package is not None:
            process = subprocess.Popen(
                ['avocado-software-manager', cmd, package],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)

            while process.poll() is None:
                time.sleep(nrunner.RUNNER_RUN_STATUS_INTERVAL)
                yield self.prepare_status('running')

            result = 'pass'
            if process.returncode == exit_codes.UTILITY_FAIL:
                result = 'error'

            returncode = process.returncode
            stdout = process.stdout.read()
            stderr = process.stderr.read()
        else:
            # Otherwise, log the missing package name
            returncode = 1
            result = 'error'
            stdout = ''
            stderr = ('Package name should be passed as kwargs using'
                      ' name="package_name".')

        yield self.prepare_status('finished',
                                  {'result': result,
                                   'returncode': returncode,
                                   'stdout': stdout,
                                   'stderr': stderr})


class RunnerApp(nrunner.BaseRunnerApp):
    PROG_NAME = 'avocado-runner-requirement-package'
    PROG_DESCRIPTION = ('nrunner application for requirements of type package')
    RUNNABLE_KINDS_CAPABLE = {'requirement-package': RequirementPackageRunner}


def main():
    nrunner.main(RunnerApp)


if __name__ == '__main__':
    main()
