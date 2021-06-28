from avocado.core import nrunner
from avocado.core.runners.utils.messages import FinishedMessage, StartedMessage


class MagicRunner(nrunner.BaseRunner):
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

    def run(self):
        yield StartedMessage.get()
        if self.runnable.uri in ['pass', 'fail']:
            result = self.runnable.uri
        else:
            result = 'error'
        yield FinishedMessage.get(result)


class RunnerApp(nrunner.BaseRunnerApp):
    PROG_NAME = 'avocado-runner-magic'
    PROG_DESCRIPTION = 'nrunner application for magic tests'
    RUNNABLE_KINDS_CAPABLE = {'magic': MagicRunner}


def main():
    nrunner.main(RunnerApp)


if __name__ == '__main__':
    main()
