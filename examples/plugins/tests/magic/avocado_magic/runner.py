from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import BaseRunner
from avocado.core.utils.messages import FinishedMessage, StartedMessage


class MagicRunner(BaseRunner):
    """Runner for magic words

    When creating the Runnable, use the following attributes:

     * kind: should be 'magic';

     * uri: the magic word, either "pass" or "fail";

     * args: not used;

     * kwargs: not used;

    Example:

       runnable = Runnable(kind='magic',
                           uri='pass')
    """

    def run(self, runnable):
        yield StartedMessage.get()
        if runnable.uri in ['pass', 'fail']:
            result = runnable.uri
        else:
            result = 'error'
        yield FinishedMessage.get(result)


class RunnerApp(BaseRunnerApp):
    PROG_NAME = 'avocado-runner-magic'
    PROG_DESCRIPTION = 'nrunner application for magic tests'
    RUNNABLE_KINDS_CAPABLE = ['magic']


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == '__main__':
    main()
