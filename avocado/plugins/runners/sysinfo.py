import multiprocessing
import os
import time
import traceback

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import (RUNNER_RUN_CHECK_INTERVAL,
                                         RUNNER_RUN_STATUS_INTERVAL,
                                         BaseRunner)
from avocado.core.utils import messages
from avocado.utils import sysinfo as sysinfo_collectible
from avocado.utils.software_manager import manager


class PreSysInfo:
    """
    Log different system properties before start event.

    An event may be a job, a test, or any other event with a
    beginning and end.
    """
    sysinfo_dir = os.path.join('sysinfo', 'pre')

    def __init__(self, config, sysinfo_config, queue):
        """
        Set sysinfo collectibles.

        :param config: avocado configuration
        :type config: dict
        :param sysinfo_config: dictionary with commands/tasks which should be
                              performed during the sysinfo collection.
        :type sysinfo_config: dict
        :param queue: queue for the runner messages
        :type queue: multiprocessing.SimpleQueue
        """
        self.config = config
        self.queue = queue
        self.log_packages = self.config.get('sysinfo.collect.installed_packages')
        self.timeout = self.config.get('sysinfo.collect.commands_timeout')
        self.locale = self.config.get('sysinfo.collect.locale')

        self.sysinfo_config = sysinfo_config
        self.collectibles = set()

    @property
    def installed_pkgs(self):
        sm = manager.SoftwareManager()
        return sm.list_all()

    def _set_collectibles(self):
        for cmd in self.sysinfo_config.get("commands", []):
            self.collectibles.add(
                sysinfo_collectible.Command(cmd, timeout=self.timeout,
                                            locale=self.locale))

        for filename in self.sysinfo_config.get("files", []):
            self.collectibles.add(sysinfo_collectible.Logfile(filename))

    def _save_sysinfo(self, log_hook):
        try:
            file_path = os.path.join(self.sysinfo_dir, log_hook.name)
            for data in log_hook.collect():
                self.queue.put(messages.FileMessage.get(data, file_path))
        except sysinfo_collectible.CollectibleException as e:
            self.queue.put(messages.LogMessage.get(e.args[0]))
        except Exception as exc:  # pylint: disable=W0703
            self.queue.put(messages.StderrMessage.get(f"Collection "
                                                      f"{type(log_hook)} "
                                                      f"failed: {exc}"))

    def collect(self):
        """Log all collectibles at the start of the event."""
        self._set_collectibles()
        for log_hook in self.collectibles:
            self._save_sysinfo(log_hook)

        if self.log_packages:
            self._log_packages(self.sysinfo_dir)
        self.queue.put(messages.FinishedMessage.get('pass'))

    def _log_packages(self, path):
        installed_path = os.path.join(path, "installed_packages")
        installed_packages = "\n".join(self.installed_pkgs) + "\n"
        self.queue.put(messages.FileMessage.get(installed_packages,
                                                installed_path))


class PostSysInfo(PreSysInfo):
    """
    Log different system properties after end event.

    An event may be a job, a test, or any other event with a
    beginning and end.
    """

    sysinfo_dir = os.path.join('sysinfo', 'post')

    def __init__(self, config, sysinfo_config, queue, test_fail=False):
        """
        :param test_fail: flag for fail tests. Default False
        :type test_fail: bool
        """
        self.test_fail = test_fail
        super().__init__(config, sysinfo_config, queue)

    def _set_collectibles(self):
        super()._set_collectibles()
        if self.test_fail:
            for fail_cmd in self.sysinfo_config.get("fail_commands", []):
                self.collectibles.add(
                    sysinfo_collectible.Command(fail_cmd, timeout=self.timeout,
                                                locale=self.locale))

            for fail_filename in self.sysinfo_config.get("fail_files", []):
                self.collectibles.add(sysinfo_collectible.Logfile(fail_filename))


class SysinfoRunner(BaseRunner):
    """
    Runner for gathering sysinfo

    Runnable attributes usage:

     * uri: sysinfo type pre/post. This variable decides if the sysinfo is
            collected before or after the test.

     * kwargs: "sysinfo" dictionary with commands/tasks which should be
               performed during the sysinfo collection.
    """

    name = 'sysinfo'
    description = 'Runner for gathering sysinfo'

    CONFIGURATION_USED = ['sysinfo.collect.installed_packages',
                          'sysinfo.collect.commands_timeout',
                          'sysinfo.collect.locale']

    def run(self, runnable):
        # pylint: disable=W0201
        self.runnable = runnable
        yield self.prepare_status('started')
        sysinfo_config = self.runnable.kwargs.get('sysinfo', {})
        test_fail = self.runnable.kwargs.get('test_fail', False)
        if self.runnable.uri not in ['pre', 'post']:
            yield messages.StderrMessage.get(f"Unsupported uri"
                                             f"{self.runnable.uri}. "
                                             f"Possible values, 'pre', 'post'")
            yield messages.FinishedMessage.get('error')

        try:
            queue = multiprocessing.SimpleQueue()
            if self.runnable.uri == 'pre':
                sysinfo = PreSysInfo(self.runnable.config,
                                     sysinfo_config,
                                     queue)
            else:
                sysinfo = PostSysInfo(self.runnable.config,
                                      sysinfo_config,
                                      queue,
                                      test_fail)
            sysinfo_process = multiprocessing.Process(target=sysinfo.collect)

            sysinfo_process.start()

            most_current_execution_state_time = None
            while True:
                time.sleep(RUNNER_RUN_CHECK_INTERVAL)
                now = time.monotonic()
                if queue.empty():
                    if most_current_execution_state_time is not None:
                        next_execution_state_mark = (most_current_execution_state_time +
                                                     RUNNER_RUN_STATUS_INTERVAL)
                    if (most_current_execution_state_time is None or
                            now > next_execution_state_mark):
                        most_current_execution_state_time = now
                        yield messages.RunningMessage.get()
                else:
                    message = queue.get()
                    yield message
                    if message.get('status') == 'finished':
                        break
        except Exception:  # pylint: disable=W0703
            yield messages.StderrMessage.get(traceback.format_exc())
            yield messages.FinishedMessage.get('error')


class RunnerApp(BaseRunnerApp):
    PROG_NAME = 'avocado-runner-sysinfo'
    PROG_DESCRIPTION = 'nrunner application for gathering sysinfo'
    RUNNABLE_KINDS_CAPABLE = ['sysinfo']


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == '__main__':
    main()
