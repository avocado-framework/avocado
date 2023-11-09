import signal
import time

from avocado_rogue import MAGIC_WORD

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import RUNNER_RUN_STATUS_INTERVAL, BaseRunner
from avocado.core.utils.messages import FinishedMessage, RunningMessage, StartedMessage


class RogueRunner(BaseRunner):
    """A rogue runner (that doesn't like to be stopped)

    When creating the Runnable, use the following attributes:

     * kind: should be 'rogue';

     * uri: the rogue magic word (-*-*-magic-word-for-rogue-*-*-)

     * args: not used;

     * kwargs: not used;

    Example:

       runnable = Runnable(kind='rogue',
                           uri='x-avocado-runner-rogue')
    """

    name = "rogue"
    description = "A rogue runner (that doesn't like to be stopped)"

    def run(self, runnable):
        yield StartedMessage.get()
        if runnable.uri == MAGIC_WORD:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            signal.signal(signal.SIGQUIT, signal.SIG_IGN)
            signal.signal(signal.SIGTSTP, signal.SIG_IGN)
            while True:
                yield RunningMessage.get()
                time.sleep(RUNNER_RUN_STATUS_INTERVAL)
        else:
            yield FinishedMessage.get("error")


class RunnerApp(BaseRunnerApp):
    PROG_NAME = "avocado-runner-rogue"
    PROG_DESCRIPTION = "nrunner application for rogue tests"
    RUNNABLE_KINDS_CAPABLE = ["rogue"]


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == "__main__":
    main()
