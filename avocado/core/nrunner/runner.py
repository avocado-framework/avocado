import multiprocessing
import signal
import time
import traceback

from avocado.core.exceptions import TestInterrupt
from avocado.core.nrunner.runnable import RUNNERS_REGISTRY_STANDALONE_EXECUTABLE
from avocado.core.plugin_interfaces import RunnableRunner
from avocado.core.utils import messages

#: The amount of time (in seconds) between each internal status check
RUNNER_RUN_CHECK_INTERVAL = 0.01

#: The amount of time (in seconds) between a status report from a
#: runner that performs its work asynchronously
RUNNER_RUN_STATUS_INTERVAL = 0.5


def check_runnables_runner_requirements(runnables, runners_registry=None):
    """
    Checks if runnables have runner requirements fulfilled

    :param runnables: the tasks whose runner requirements will be checked
    :type runnables: list of :class:`Runnable`
    :param runners_registry: a registry with previously found (and not found)
                             runners keyed by a task's runnable kind. Defaults
                             to :attr:`RUNNERS_REGISTRY_STANDALONE_EXECUTABLE`
    :type runners_registry: dict
    :return: two list of tasks in a tuple, with the first being the tasks
             that pass the requirements check and the second the tasks that
             fail the requirements check
    :rtype: tuple of (list, list)
    """
    if runners_registry is None:
        runners_registry = RUNNERS_REGISTRY_STANDALONE_EXECUTABLE
    ok = []
    missing = []

    for runnable in runnables:
        runner = runnable.pick_runner_command(runnable.kind, runners_registry)
        if runner:
            ok.append(runnable)
        else:
            missing.append(runnable)
    return (ok, missing)


class BaseRunner(RunnableRunner):

    #: The "main Avocado" configuration keys (AKA namespaces) that
    #: this runners makes use of.
    CONFIGURATION_USED = []

    @staticmethod
    def signal_handler(signum, frame):  # pylint: disable=W0613
        if signum == signal.SIGTERM.value:
            raise TestInterrupt("Test interrupted: Timeout reached")

    @staticmethod
    def prepare_status(status_type, additional_info=None):
        """Prepare a status dict with some basic information.

        This will add the keyword 'status' and 'time' to all status.

        :param: status_type: The type of event ('started', 'running',
                             'finished')
        :param: addional_info: Any additional information that you
                               would like to add to the dict. This must be a
                               dict.

        :rtype: dict
        """
        status = {}
        if isinstance(additional_info, dict):
            status = additional_info
        status.update({"status": status_type, "time": time.monotonic()})
        return status

    @staticmethod
    def _monitor(queue):
        most_recent_status_time = None
        while True:
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)
            if queue.empty():
                now = time.monotonic()
                if (
                    most_recent_status_time is None
                    or now >= most_recent_status_time + RUNNER_RUN_STATUS_INTERVAL
                ):
                    most_recent_status_time = now
                    yield messages.RunningMessage.get()
                continue
            else:
                message = queue.get()
                yield message
                if message.get("status") == "finished":
                    break

    def _catch_errors(self, runnable, queue):
        """Wrapper around runners methods for catching and logging failures."""
        try:
            messages.start_logging(runnable.config, queue)
            signal.signal(signal.SIGTERM, self.signal_handler)
            for message in self._run(runnable):
                queue.put(message)
        except TestInterrupt as e:
            queue.put(messages.StderrMessage.get(str(e)))
            queue.put(messages.FinishedMessage.get("interrupted", fail_reason=str(e)))
        except Exception as e:
            queue.put(messages.StderrMessage.get(traceback.format_exc()))
            queue.put(
                messages.FinishedMessage.get(
                    "error",
                    fail_reason=str(e),
                    fail_class=e.__class__.__name__,
                    traceback=traceback.format_exc(),
                )
            )

    def run(self, runnable):
        # pylint: disable=W0201
        signal.signal(signal.SIGTERM, self.signal_handler)
        self.runnable = runnable
        yield messages.StartedMessage.get()
        try:
            queue = multiprocessing.SimpleQueue()
            process = multiprocessing.Process(
                target=self._catch_errors, args=(self.runnable, queue)
            )

            process.start()

            for message in self._monitor(queue):
                yield message

        except TestInterrupt:
            process.terminate()
            for message in self._monitor(queue):
                yield message
        except Exception as e:
            yield messages.StderrMessage.get(traceback.format_exc())
            yield messages.FinishedMessage.get(
                "error",
                fail_reason=str(e),
                fail_class=e.__class__.__name__,
                traceback=traceback.format_exc(),
            )

    def _run(self, runnable):
        """
        Run the Runnable

        :param runnable: the runnable object
        :type runnable: :class:`Runnable`
        """
