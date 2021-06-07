import logging
import multiprocessing
import os
import time
import traceback
from abc import ABC, abstractmethod

from avocado.core import nrunner
from avocado.core.runners.utils import messages
from avocado.core.settings import settings
from avocado.utils import astring, process, software_manager

__all__ = ["PreSysInfo", "PostSysInfo", "SysinfoRunner", "RunnerApp", "main"]

log = logging.getLogger("avocado.sysinfo")


class Collectible(ABC):

    """
    Abstract class for representing collectibles by sysinfo.
    """

    def __init__(self, log_path):
        self.log_path = astring.string_to_safe_path(log_path)

    def __eq__(self, other):
        if hash(self) == hash(other):
            return True
        elif isinstance(other, Collectible):
            return False
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    @abstractmethod
    def run(self, queue, logdir):
        pass


class LogFile(Collectible):

    """
    Collectible system file.

    :param path: Path to the log file.
    """

    def __init__(self, path):
        super().__init__(os.path.basename(path))
        self.path = path

    def __repr__(self):
        return "LogFile(%r, %r)" % (self.path, self.log_path)

    def __hash__(self):
        return hash((self.path, self.log_path, LogFile))

    def run(self, queue, logdir):
        """
        Send the content of log file to the runner messages queue.

        :param queue: queue for the runner messages
        :type queue: multiprocessing.SimpleQueue
        :param logdir: Path to a log directory.
        :type logdir: str
        """
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    lines = f.readlines()
                log_path = os.path.join(logdir, self.log_path)
                for line in lines:
                    queue.put(messages.FileMessage.get(line, log_path))
            except IOError:
                log.debug("Not logging %s (lack of permissions)", self.path)
        else:
            log.debug("Not logging %s (file does not exist)", self.path)


class Command(Collectible):

    """
    Collectible command.

    :param cmd: String with the command.
    :type cmd: str
    """

    def __init__(self, cmd):
        super().__init__(cmd)
        self.cmd = cmd

    def __repr__(self):
        return "Command(%r, %r)" % (self.cmd, self.log_path)

    def __hash__(self):
        return hash((self.cmd, self.log_path, Command))

    def run(self, queue, logdir):
        """
        Execute the command as a subprocess and send its output to
        the runner messages queue.

        :param queue: queue for the runner messages
        :type queue: multiprocessing.SimpleQueue
        :param logdir: Path to a log directory.
        :type logdir: str
        """
        env = os.environ.copy()
        config = settings.as_dict()
        if "PATH" not in env:
            env["PATH"] = "/usr/bin:/bin"
        locale = config.get("sysinfo.collect.locale")
        if locale:
            env["LC_ALL"] = locale
        timeout = config.get('sysinfo.collect.commands_timeout', 0)
        # the sysinfo configuration supports negative or zero integer values
        # but the avocado.utils.process APIs define no timeouts as "None"
        if int(timeout) <= 0:
            timeout = None
        try:
            result = process.run(self.cmd,
                                 timeout=timeout,
                                 verbose=False,
                                 ignore_status=True,
                                 allow_output_check='combined',
                                 shell=True,
                                 env=env)
        except FileNotFoundError as exc_fnf:
            log.debug("Not logging '%s' (command '%s' was not found)",
                      self.cmd, exc_fnf.filename)
            return
        except Exception as exc:  # pylint: disable=W0703
            log.warning('Could not execute "%s": %s', self.cmd, exc)
            return
        log_path = os.path.join(logdir, self.log_path)
        message = messages.FileMessage.get(result.stdout, log_path)
        queue.put(message)


class PreSysInfo:
    """
    Log different system properties before start event.

    An event may be a job, a test, or any other event with a
    beginning and end.
    """
    sysinfo_dir = os.path.join('sysinfo', 'pre')

    def __init__(self, config, sysinfo_files, queue):
        """
        Set sysinfo collectibles.

        :param config: avocado configuration
        :type config: dict
        :param sysinfo_files: dictionary with commands/tasks which should be
                              performed during the sysinfo collection.
        :type sysinfo_files: dict
        :param queue: queue for the runner messages
        :type queue: multiprocessing.SimpleQueue
        """
        self.config = config
        self.queue = queue
        self._installed_pkgs = None
        packages_namespace = 'sysinfo.collect.installed_packages'
        self.log_packages = self.config.get(packages_namespace, False)

        self.sysinfo_files = sysinfo_files
        self.collectibles = set()

    def _set_collectibles(self):
        for cmd in self.sysinfo_files.get("commands", []):
            self.collectibles.add(Command(cmd))

        for filename in self.sysinfo_files.get("files", []):
            self.collectibles.add(LogFile(filename))

    def _get_installed_packages(self):
        sm = software_manager.SoftwareManager()
        installed_pkgs = sm.list_all()
        self._installed_pkgs = installed_pkgs
        return installed_pkgs

    def collect(self):
        """Log all collectibles at the start of the event."""
        self._set_collectibles()
        for log_hook in self.collectibles:
            log_hook.run(self.queue, self.sysinfo_dir)

        if self.log_packages:
            self._log_packages(self.sysinfo_dir)
        self.queue.put(messages.FinishedMessage.get('pass'))

    def _log_packages(self, path):
        installed_path = os.path.join(path, "installed_packages")
        installed_packages = "\n".join(self._get_installed_packages()) + "\n"
        self.queue.put(messages.FileMessage.get(installed_packages,
                                                installed_path))


class PostSysInfo(PreSysInfo):
    """
    Log different system properties after end event.

    An event may be a job, a test, or any other event with a
    beginning and end.
    """

    sysinfo_dir = os.path.join('sysinfo', 'post')

    def __init__(self, config, sysinfo_files, queue, test_fail=False):
        """
        :param test_fail: flag for fail tests. Default False
        :type test_fail: bool
        """
        self.test_fail = test_fail
        super().__init__(config, sysinfo_files, queue)

    def _set_collectibles(self):
        super()._set_collectibles()
        if self.test_fail:
            for fail_cmd in self.sysinfo_files.get("fail_commands", []):
                self.collectibles.add(Command(fail_cmd))

            for fail_filename in self.sysinfo_files.get("fail_files", []):
                self.collectibles.add(LogFile(fail_filename))


class SysinfoRunner(nrunner.BaseRunner):
    """
    Runner for gathering sysinfo

    Runnable attributes usage:

     * uri: Specification of sysinfo. Possible values pre/post

     * kwargs: sysinfo_files dictionary with commands/tasks which should be
             performed during the sysinfo collection.
    """

    def run(self):
        yield self.prepare_status('started')
        sysinfo_files = self.runnable.kwargs.get('sysinfo_files', {})
        test_fail = self.runnable.kwargs.get('test_fail', False)
        try:
            queue = multiprocessing.SimpleQueue()
            if self.runnable.uri == 'pre':
                sysinfo = PreSysInfo(self.runnable.config,
                                     sysinfo_files,
                                     queue)
            else:
                sysinfo = PostSysInfo(self.runnable.config,
                                      sysinfo_files,
                                      queue,
                                      test_fail)
            sysinfo_process = multiprocessing.Process(target=sysinfo.collect())

            sysinfo_process.start()

            most_current_execution_state_time = None
            while True:
                time.sleep(nrunner.RUNNER_RUN_CHECK_INTERVAL)
                now = time.monotonic()
                if queue.empty():
                    if most_current_execution_state_time is not None:
                        next_execution_state_mark = (most_current_execution_state_time +
                                                     nrunner.RUNNER_RUN_STATUS_INTERVAL)
                    if (most_current_execution_state_time is None or
                            now > next_execution_state_mark):
                        most_current_execution_state_time = now
                        yield messages.RunningMessage.get()
                else:
                    message = queue.get()
                    yield message
                    if message.get('status') == 'finished':
                        break
        except Exception:
            yield messages.StderrMessage.get(traceback.format_exc())
            yield messages.FinishedMessage.get('error')


class RunnerApp(nrunner.BaseRunnerApp):
    PROG_NAME = 'avocado-runner-sysinfo'
    PROG_DESCRIPTION = 'nrunner application for gathering sysinfo'
    RUNNABLE_KINDS_CAPABLE = {'sysinfo': SysinfoRunner}


def main():
    nrunner.main(RunnerApp)


if __name__ == '__main__':
    main()
