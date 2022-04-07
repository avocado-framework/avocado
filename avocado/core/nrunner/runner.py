import time

from avocado.core.nrunner.runnable import \
    RUNNERS_REGISTRY_STANDALONE_EXECUTABLE
from avocado.core.plugin_interfaces import RunnableRunner

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
        runner = runnable.pick_runner_command(runners_registry)
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
        status.update({'status': status_type,
                       'time': time.monotonic()})
        return status
