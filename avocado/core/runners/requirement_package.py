import time
from multiprocessing import Process, SimpleQueue

from ...utils.software_manager.main import MESSAGES
from ...utils.software_manager.manager import SoftwareManager
from .. import nrunner


class RequirementPackageRunner(nrunner.BaseRunner):
    """Runner for requirements of type package

    This runner handles, the installation, verification and removal of
    packages using the avocado-software-manager.

    Runnable attributes usage:

     * kind: 'requirement-package'

     * uri: not used

     * args: not used

     * kwargs:
        - name: the package name (required)
        - action: one of 'install', 'check', or 'remove' (optional, defaults
          to 'install')
    """

    @staticmethod
    def _check(software_manager, package):
        if software_manager.check_installed(package):
            result = 'pass'
            stdout = MESSAGES['check-installed']['success'] % package
            stderr = ''
        else:
            result = 'error'
            stdout = ''
            stderr = MESSAGES['check-installed']['fail'] % package
        return result, stdout, stderr

    @staticmethod
    def _install(software_manager, cmd, package):
        result = 'pass'
        stderr = ''
        if not software_manager.check_installed(package):
            if software_manager.install(package):
                stdout = MESSAGES[cmd]['success'] % package
            else:
                result = 'error'
                stdout = ''
                stderr = MESSAGES[cmd]['fail'] % package
        else:
            stdout = MESSAGES['check-installed']['success'] % package
        return result, stdout, stderr

    @staticmethod
    def _remove(software_manager, cmd, package):
        result = 'pass'
        stderr = ''
        if software_manager.check_installed(package):
            if software_manager.remove(package):
                stdout = MESSAGES[cmd]['success'] % package
            else:
                result = 'error'
                stdout = ''
                stderr = MESSAGES[cmd]['fail'] % package
        else:
            stdout = MESSAGES['check-installed']['fail'] % package
        return result, stdout, stderr

    def _run_software_manager(self, cmd, package, queue):
        software_manager = SoftwareManager()

        if not software_manager.is_capable():
            output = {'result': 'error',
                      'stdout': '',
                      'stderr': ('Package manager not supported or not'
                                 ' available.')}
            queue.put(output)

        if cmd == 'install':
            result, stdout, stderr = self._install(software_manager, cmd,
                                                   package)

        elif cmd == 'remove':
            result, stdout, stderr = self._remove(software_manager, cmd,
                                                  package)

        elif cmd == 'check':
            result, stdout, stderr = self._check(software_manager, package)

        output = {'result': result,
                  'stdout': stdout,
                  'stderr': stderr}
        queue.put(output)

    def run(self):
        yield self.prepare_status('started')
        # check if there is a valid 'action' argument
        cmd = self.runnable.kwargs.get('action', 'install')
        # avoid invalid arguments
        if cmd not in ['install', 'check', 'remove']:
            stderr = ("Invalid action %s. Use one of 'install', 'check' or"
                      " 'remove'" % cmd)
            yield self.prepare_status('running',
                                      {'type': 'stderr', 'log': stderr})
            yield self.prepare_status('finished', {'result': 'error'})
            return

        package = self.runnable.kwargs.get('name')
        # if package was passed correctly, run avocado-software-manager
        if package is not None:
            # let's spawn it to another process to be able to update the
            # status messages and avoid the software-manager to lock this
            # process
            queue = SimpleQueue()
            process = Process(target=self._run_software_manager,
                              args=(cmd, package, queue))
            process.start()

            while queue.empty():
                time.sleep(nrunner.RUNNER_RUN_STATUS_INTERVAL)
                yield self.prepare_status('running')

            output = queue.get()
            result = output['result']
            stdout = output['stdout']
            stderr = output['stderr']
        else:
            # Otherwise, log the missing package name
            result = 'error'
            stdout = ''
            stderr = ('Package name should be passed as kwargs using'
                      ' name="package_name".')

        yield self.prepare_status('running',
                                  {'type': 'stdout',
                                   'log': stdout.encode()})
        yield self.prepare_status('running',
                                  {'type': 'stderr',
                                   'log': stderr.encode()})
        yield self.prepare_status('finished', {'result': result})


class RunnerApp(nrunner.BaseRunnerApp):
    PROG_NAME = 'avocado-runner-requirement-package'
    PROG_DESCRIPTION = ('nrunner application for requirements of type package')
    RUNNABLE_KINDS_CAPABLE = {'requirement-package': RequirementPackageRunner}


def main():
    nrunner.main(RunnerApp)


if __name__ == '__main__':
    main()
