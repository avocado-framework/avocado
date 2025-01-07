import multiprocessing
import os
import sys

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import BaseRunner
from avocado.core.utils import messages
from avocado.utils import sysinfo as sysinfo_collectible
from avocado.utils.software_manager import manager


class PreSysInfo:
    """
    Log different system properties before start event.

    An event may be a job, a test, or any other event with a
    beginning and end.
    """

    sysinfo_dir = os.path.join("sysinfo", "pre")

    def __init__(self, config, sysinfo_config):
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
        self.log_packages = self.config.get("sysinfo.collect.installed_packages")
        self.timeout = self.config.get("sysinfo.collect.commands_timeout")
        self.locale = self.config.get("sysinfo.collect.locale")

        self.sysinfo_config = sysinfo_config
        self.collectibles = set()

    @property
    def installed_pkgs(self):
        sm = manager.SoftwareManager()
        return sm.list_all()

    def _set_collectibles(self):
        for cmd in self.sysinfo_config.get("commands", []):
            self.collectibles.add(
                sysinfo_collectible.Command(
                    cmd, timeout=self.timeout, locale=self.locale
                )
            )

        for filename in self.sysinfo_config.get("files", []):
            self.collectibles.add(sysinfo_collectible.Logfile(filename))

    def collect(self):
        """Log all collectibles at the start of the event."""
        self._set_collectibles()
        for log_hook in self.collectibles:
            try:
                file_path = os.path.join(self.sysinfo_dir, log_hook.name)
                for data in log_hook.collect():
                    yield messages.FileMessage.get(data, file_path)
            except sysinfo_collectible.CollectibleException as e:
                yield messages.LogMessage.get(e.args[0])
            except Exception as exc:  # pylint: disable=W0703
                yield messages.StderrMessage.get(
                    f"Collection " f"{type(log_hook)} " f"failed: {exc}"
                )

        if self.log_packages:
            yield self._log_packages(self.sysinfo_dir)
        yield messages.FinishedMessage.get("pass")

    def _log_packages(self, path):
        installed_path = os.path.join(path, "installed_packages")
        installed_packages = "\n".join(self.installed_pkgs) + "\n"
        return messages.FileMessage.get(installed_packages, installed_path)


class PostSysInfo(PreSysInfo):
    """
    Log different system properties after end event.

    An event may be a job, a test, or any other event with a
    beginning and end.
    """

    sysinfo_dir = os.path.join("sysinfo", "post")

    def __init__(self, config, sysinfo_config, test_fail=False):
        """
        :param test_fail: flag for fail tests. Default False
        :type test_fail: bool
        """
        self.test_fail = test_fail
        super().__init__(config, sysinfo_config)

    def _set_collectibles(self):
        super()._set_collectibles()
        if self.test_fail:
            for fail_cmd in self.sysinfo_config.get("fail_commands", []):
                self.collectibles.add(
                    sysinfo_collectible.Command(
                        fail_cmd, timeout=self.timeout, locale=self.locale
                    )
                )

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

    name = "sysinfo"
    description = "Runner for gathering sysinfo"

    CONFIGURATION_USED = [
        "sysinfo.collect.installed_packages",
        "sysinfo.collect.commands_timeout",
        "sysinfo.collect.locale",
    ]

    def _run(self, runnable):
        # pylint: disable=W0201
        sysinfo_config = runnable.kwargs.get("sysinfo", {})
        test_fail = runnable.kwargs.get("test_fail", False)
        if runnable.uri not in ["pre", "post"]:
            yield messages.StderrMessage.get(
                f"Unsupported uri "
                f"{self.runnable.uri}. "
                f"Possible values, 'pre', 'post'"
            )
            yield messages.FinishedMessage.get("error")

        if self.runnable.uri == "pre":
            sysinfo = PreSysInfo(self.runnable.config, sysinfo_config)
        else:
            sysinfo = PostSysInfo(self.runnable.config, sysinfo_config, test_fail)
        for message in sysinfo.collect():
            yield message


class RunnerApp(BaseRunnerApp):
    PROG_NAME = "avocado-runner-sysinfo"
    PROG_DESCRIPTION = "nrunner application for gathering sysinfo"
    RUNNABLE_KINDS_CAPABLE = ["sysinfo"]


def main():
    if sys.platform == "darwin":
        multiprocessing.set_start_method("fork")
    app = RunnerApp(print)
    app.run()


if __name__ == "__main__":
    main()
