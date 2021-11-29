# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# This code was inspired in the autotest project,
# client/shared/settings.py
# Author: John Admanski <jadmanski@google.com>
import filecmp
import logging
import os
import time

from avocado.core import output
from avocado.core.settings import settings
from avocado.utils import genio
from avocado.utils import path as utils_path
from avocado.utils import software_manager, sysinfo

log = logging.getLogger("avocado.sysinfo")


def gather_collectibles_config(config):
    sysinfo_files = {}

    for collectible in ['commands', 'files', 'fail_commands', 'fail_files']:
        tmp_file = config.get('sysinfo.collectibles.%s' % collectible)
        if os.path.isfile(tmp_file):
            log.info('%s configured by file: %s', collectible.title(),
                     tmp_file)
            sysinfo_files[collectible] = genio.read_all_lines(tmp_file)
        else:
            log.debug('File %s does not exist.', tmp_file)
            sysinfo_files[collectible] = []

        if 'fail_' in collectible:
            list1 = sysinfo_files[collectible]
            list2 = sysinfo_files[collectible.split('_')[1]]
            sysinfo_files[collectible] = [
                tmp for tmp in list1 if tmp not in list2]
    return sysinfo_files


class SysInfo:

    """
    Log different system properties at some key control points.

    Includes support for a start and stop event, with daemons running in
    between.  An event may be a job, a test, or any other event with a
    beginning and end.
    """

    def __init__(self, basedir=None, log_packages=None, profiler=None):
        """
        Set sysinfo collectibles.

        :param basedir: Base log dir where sysinfo files will be located.
        :param log_packages: Whether to log system packages (optional because
                             logging packages is a costly operation). If not
                             given explicitly, tries to look in the config
                             files, and if not found, defaults to False.
        :param profiler: Whether to use the profiler. If not given explicitly,
                         tries to look in the config files.
        """
        self.config = settings.as_dict()

        if basedir is None:
            basedir = utils_path.init_dir('sysinfo')
        self.basedir = basedir

        self._installed_pkgs = None
        if log_packages is None:
            packages_namespace = 'sysinfo.collect.installed_packages'
            self.log_packages = self.config.get(packages_namespace)
        else:
            self.log_packages = log_packages

        self._get_collectibles(profiler)

        self.start_collectibles = set()
        self.end_collectibles = set()
        self.end_fail_collectibles = set()

        self.pre_dir = utils_path.init_dir(self.basedir, 'pre')
        self.post_dir = utils_path.init_dir(self.basedir, 'post')
        self.profile_dir = utils_path.init_dir(self.basedir, 'profile')

        self._set_collectibles()

    def _get_collectibles(self, c_profiler):
        self.sysinfo_files = gather_collectibles_config(self.config)

        profiler = c_profiler
        if profiler is None:
            self.profiler = self.config.get('sysinfo.collect.profiler')
        else:
            self.profiler = profiler

        profiler_file = self.config.get('sysinfo.collectibles.profilers')
        if os.path.isfile(profiler_file):
            self.sysinfo_files["profilers"] = genio.read_all_lines(
                profiler_file)
            log.info('Profilers configured by file: %s', profiler_file)
            if not self.sysinfo_files["profilers"]:
                self.profiler = False

            if self.profiler is False:
                if not self.sysinfo_files["profilers"]:
                    log.info('Profiler disabled: no profiler'
                             ' commands configured')
                else:
                    log.info('Profiler disabled')
        else:
            log.debug('File %s does not exist.', profiler_file)
            self.sysinfo_files["profilers"] = []

    @staticmethod
    def _get_syslog_watcher():
        logpaths = ["/var/log/messages",
                    "/var/log/syslog",
                    "/var/log/system.log"]
        for logpath in logpaths:
            if os.path.exists(logpath):
                try:
                    return sysinfo.LogWatcher(logpath)
                except PermissionError as e:
                    log.debug(e.args[0])
        raise ValueError("System log file not found (looked for %s)" %
                         logpaths)

    def _set_collectibles(self):
        timeout = self.config.get('sysinfo.collect.commands_timeout')
        locale = self.config.get('sysinfo.collect.locale')
        if self.profiler:
            for cmd in self.sysinfo_files["profilers"]:
                self.start_collectibles.add(sysinfo.Daemon(cmd, locale=locale))

        for cmd in self.sysinfo_files["commands"]:
            self.start_collectibles.add(sysinfo.Command(cmd, timeout=timeout,
                                                        locale=locale))
            self.end_collectibles.add(sysinfo.Command(cmd, timeout=timeout,
                                                      locale=locale))

        for fail_cmd in self.sysinfo_files["fail_commands"]:
            self.end_fail_collectibles.add(sysinfo.Command(fail_cmd,
                                                           timeout=timeout,
                                                           locale=locale))

        for filename in self.sysinfo_files["files"]:
            self.start_collectibles.add(sysinfo.Logfile(filename))
            self.end_collectibles.add(sysinfo.Logfile(filename))

        for fail_filename in self.sysinfo_files["fail_files"]:
            self.end_fail_collectibles.add(sysinfo.Logfile(fail_filename))
        try:
            self.end_collectibles.add(sysinfo.JournalctlWatcher())
        except sysinfo.CollectibleException as e:
            log.debug(e.args[0])

    def _get_installed_packages(self):
        sm = software_manager.SoftwareManager()
        installed_pkgs = sm.list_all()
        self._installed_pkgs = installed_pkgs
        return installed_pkgs

    def _log_installed_packages(self, path):
        installed_path = os.path.join(path, "installed_packages")
        installed_packages = "\n".join(self._get_installed_packages()) + "\n"
        genio.write_file(installed_path, installed_packages)

    def _log_modified_packages(self, path):
        """
        Log any changes to installed packages.
        """
        old_packages = set(self._installed_pkgs)
        new_packages = set(self._get_installed_packages())
        added_path = os.path.join(path, "added_packages")
        added_packages = "\n".join(new_packages - old_packages) + "\n"
        genio.write_file(added_path, added_packages)
        removed_path = os.path.join(self.basedir, "removed_packages")
        removed_packages = "\n".join(old_packages - new_packages) + "\n"
        genio.write_file(removed_path, removed_packages)

    def _save_sysinfo(self, log_hook, sysinfo_dir, optimized=False):
        try:
            file_path = os.path.join(sysinfo_dir, log_hook.name)
            with open(file_path, "wb") as log_file:
                for data in log_hook.collect():
                    log_file.write(data)
            if optimized:
                self._optimize(log_hook)
        except sysinfo.CollectibleException as e:
            log.debug(e.args[0])
        except Exception as exc:  # pylint: disable=W0703
            log.error("Collection %s failed: %s", type(log_hook), exc)

    def _optimize(self, log_hook):
        pre_file = os.path.join(self.pre_dir, log_hook.name)
        post_file = os.path.join(self.post_dir, log_hook.name)
        if filecmp.cmp(pre_file, post_file):
            os.remove(post_file)
            log.debug("Not logging %s (no change detected)", log_hook.name)

    def start(self):
        """Log all collectibles at the start of the event."""
        os.environ['AVOCADO_SYSINFODIR'] = self.pre_dir
        for log_hook in self.start_collectibles:
            # log daemons in profile directory
            if isinstance(log_hook, sysinfo.Daemon):
                try:
                    log_hook.run()
                except sysinfo.CollectibleException as e:
                    log.debug(e.args[0])
            else:
                self._save_sysinfo(log_hook, self.pre_dir)

        if self.log_packages:
            self._log_installed_packages(self.pre_dir)

    def end(self, status=""):
        """
        Logging hook called whenever a job finishes.
        """
        optimized = self.config.get('sysinfo.collect.optimize')
        os.environ['AVOCADO_SYSINFODIR'] = self.post_dir
        for log_hook in self.end_collectibles:
            self._save_sysinfo(log_hook, self.post_dir, optimized)

        if status == "FAIL":
            for log_hook in self.end_fail_collectibles:
                self._save_sysinfo(log_hook, self.post_dir, optimized)

        # Stop daemon(s) started previously
        for log_hook in self.start_collectibles:
            if isinstance(log_hook, sysinfo.Daemon):
                self._save_sysinfo(log_hook, self.post_dir)
        if self.log_packages:
            self._log_modified_packages(self.post_dir)


def collect_sysinfo(basedir):
    """
    Collect sysinfo to a base directory.
    """
    output.add_log_handler(log.name)
    if not basedir:
        cwd = os.getcwd()
        timestamp = time.strftime('%Y-%m-%d-%H.%M.%S')
        basedir = os.path.join(cwd, 'sysinfo-%s' % timestamp)

    sysinfo_logger = SysInfo(basedir=basedir)
    sysinfo_logger.start()
    sysinfo_logger.end()
    log.info("Logged system information to %s", basedir)
