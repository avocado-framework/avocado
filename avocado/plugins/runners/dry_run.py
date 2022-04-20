from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import BaseRunner


class DryRunRunner(BaseRunner):
    """
    Runner for --dry-run.

    It performs no action before reporting FINISHED status with cancel result.

    Runnable attributes usage:

     * uri: not used

     * args: not used
    """

    name = 'dry-run'
    description = 'Runner for --dry-run'

    def run(self, runnable):
        yield self.prepare_status('started')
        yield self.prepare_status('finished',
                                  {'result': 'cancel',
                                   'fail_reason': 'Test cancelled due to '
                                                  '--dry-run'})


class RunnerApp(BaseRunnerApp):
    PROG_NAME = 'avocado-runner-dry-run'
    PROG_DESCRIPTION = 'nrunner application for dry-run tests'
    RUNNABLE_KINDS_CAPABLE = ['dry-run']


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == '__main__':
    main()
