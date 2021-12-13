from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.registry import RUNNERS_REGISTRY_PYTHON_CLASS
from avocado.core.nrunner.runner import BaseRunner


class NoOpRunner(BaseRunner):
    """
    Sample runner that performs no action before reporting FINISHED status

    Runnable attributes usage:

     * uri: not used

     * args: not used
    """

    def run(self):
        yield self.prepare_status('started')
        yield self.prepare_status('finished', {'result': 'pass'})


RUNNERS_REGISTRY_PYTHON_CLASS['noop'] = NoOpRunner


class RunnerApp(BaseRunnerApp):
    PROG_NAME = 'avocado-runner-noop'
    PROG_DESCRIPTION = 'nrunner application for noop tests'
    RUNNABLE_KINDS_CAPABLE = {
        'noop': NoOpRunner
    }


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == '__main__':
    main()
