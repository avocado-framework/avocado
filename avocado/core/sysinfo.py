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
import json
import logging
import os
import shlex
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod

from ..utils import astring, genio
from ..utils import path as utils_path
from ..utils import process, software_manager
from . import output
from .settings import settings

log = logging.getLogger("avocado.sysinfo")

DATA_SIZE = 200000


class Collectible(ABC):

    """
    Abstract class for representing sysinfo collectibles.
    """

    def __init__(self, log_path):
        self.log_path = astring.string_to_safe_path(log_path)
        self._name = os.path.basename(log_path)

    @abstractmethod
    def collect(self):
        pass

    @property
    def name(self):
        return self._name

    @staticmethod
    def _read_file(path, bytes_to_skip=0):
        """Method for lazy reading of file"""
        with open(path, "rb") as in_messages:
            in_messages.seek(bytes_to_skip)
            while True:
                # Read data in manageable chunks rather than
                # all at once.
                in_data = in_messages.read(DATA_SIZE)
                if not in_data:
                    break
                yield in_data

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

    def __hash__(self):
        return hash((self.log_path, Collectible))


class Logfile(Collectible):

    """
    Collectible system file.

    :param path: Path to the log file.
    :param log_path: Basename of the file where output is logged (optional).
    """

    def __init__(self, path, log_path=None):
        if not log_path:
            log_path = os.path.basename(path)
        super(Logfile, self).__init__(log_path)
        self.path = path

    def __repr__(self):
        r = "Logfile(%r, %r)"
        r %= (self.path, self.log_path)
        return r

    def __eq__(self, other):
        if isinstance(other, Logfile):
            return (self.path, self.log_path) == (other.path, other.log_path)
        elif isinstance(other, Collectible):
            return False
        return NotImplemented

    def __hash__(self):
        return hash((self.path, self.log_path, Logfile))

    def collect(self):
        """
        Reads the log file.
        :raise CollectibleException
        """
        if os.path.exists(self.path):
            try:
                yield from self._read_file(self.path)
            except IOError:
                log.debug("Not logging %s (lack of permissions)", self.path)
        else:
            log.debug("Not logging %s (file does not exist)", self.path)


class Command(Collectible):

    """
    Collectible command.
    :param cmd: String with the command.
    :param timeout: Timeout for command execution.
    :param locale: Force LANG for sysinfo collection
    """

    def __init__(self, cmd, timeout=-1, locale='C'):
        super(Command, self).__init__(cmd)
        self._name = self.log_path
        self.cmd = cmd
        self.timeout = timeout
        self.locale = locale

    def __repr__(self):
        r = "Command(%r, %r)"
        r %= (self.cmd, self.log_path)
        return r

    def __eq__(self, other):
        if isinstance(other, Command):
            return (self.cmd, self.log_path) == (other.cmd, other.log_path)
        elif isinstance(other, Collectible):
            return False
        return NotImplemented

    def __hash__(self):
        return hash((self.cmd, self.log_path, Command))

    def collect(self):
        """
        Execute the command as a subprocess and returns it's output.
        :raise CollectibleException
        """
        env = os.environ.copy()
        if "PATH" not in env:
            env["PATH"] = "/usr/bin:/bin"
        if self.locale:
            env["LC_ALL"] = self.locale
        # the sysinfo configuration supports negative or zero integer values
        # but the avocado.utils.process APIs define no timeouts as "None"
        if int(self.timeout) <= 0:
            self.timeout = None
        try:
            result = process.run(self.cmd,
                                 timeout=self.timeout,
                                 verbose=False,
                                 ignore_status=True,
                                 allow_output_check='combined',
                                 shell=True,
                                 env=env)
            yield result.stdout

        except FileNotFoundError as exc_fnf:
            log.debug("Not logging '%s' (command '%s' was not found)", self.cmd,
                      exc_fnf.filename)
        except Exception as exc:  # pylint: disable=W0703
            log.warning('Could not execute "%s": %s', self.cmd, exc)


class Daemon(Command):

    """
    Collectible daemon.
    :param cmd: String with the command.
    :param timeout: Timeout for command execution.
    :param locale: Force LANG for sysinfo collection
    """

    def __init__(self, *args, **kwargs):
        super(Daemon, self).__init__(*args, **kwargs)
        self.daemon_process = None
        self.temp_file = tempfile.NamedTemporaryFile()

    def __repr__(self):
        r = "Daemon(%r, %r)"
        r %= (self.cmd, self.log_path)
        return r

    def __eq__(self, other):
        if isinstance(other, Daemon):
            return (self.cmd, self.log_path) == (other.cmd, other.log_path)
        elif isinstance(other, Collectible):
            return False
        return NotImplemented

    def __hash__(self):
        return hash((self.cmd, self.log_path, Daemon))

    def __del__(self):
        self.temp_file.close()

    def run(self):
        """
        Start running the daemon as a subprocess.
        :raise CollectibleException
        """
        env = os.environ.copy()
        if "PATH" not in env:
            env["PATH"] = "/usr/bin:/bin"
        if self.locale:
            env["LC_ALL"] = self.locale
        logf_path = self.temp_file.name
        stdin = open(os.devnull, "r")
        stdout = open(logf_path, "w")

        try:
            self.daemon_process = subprocess.Popen(shlex.split(self.cmd),
                                                   stdin=stdin, stdout=stdout,
                                                   stderr=subprocess.STDOUT,
                                                   shell=False, env=env)
        except OSError:
            log.debug("Not logging  %s (command could not be run)", self.cmd)

    def collect(self):
        """
        Stop daemon execution and returns it's logs.
        :raise OSError
        """
        if self.daemon_process is not None:
            retcode = self.daemon_process.poll()
            if retcode is None:
                process.kill_process_tree(self.daemon_process.pid)
                self.daemon_process.wait()
                for line in self.temp_file.readlines():
                    yield line
            else:
                log.error("Daemon process '%s' (pid %d) "
                          "terminated abnormally (code %d)",
                          self.cmd, self.daemon_process.pid, retcode)


class JournalctlWatcher(Collectible):

    """
    Track the content of systemd journal.

    :param log_path: Basename of the file where output is logged (optional).
    """

    def __init__(self, log_path=None):
        if not log_path:
            log_path = 'journalctl.gz'

        super(JournalctlWatcher, self).__init__(log_path)
        self.cursor = self._get_cursor()

    def __repr__(self):
        r = "JournalctlWatcher(%r)"
        r %= self.log_path
        return r

    def __eq__(self, other):
        if isinstance(other, JournalctlWatcher):
            return self.log_path == other.log_path
        elif isinstance(other, Collectible):
            return False
        return NotImplemented

    def __hash__(self):
        return hash((self.log_path, JournalctlWatcher))

    @staticmethod
    def _get_cursor():
        try:
            cmd = 'journalctl --quiet --lines 1 --output json'
            result = process.system_output(cmd, verbose=False)
            last_record = json.loads(astring.to_text(result, "utf-8"))
            return last_record['__CURSOR']
        except Exception as detail:  # pylint: disable=W0703
            log.debug("Journalctl collection failed: %s", detail)

    def collect(self):
        """
        Returns the content of systemd journal
        :raise CollectibleException
        """
        if self.cursor:
            try:
                cmd = 'journalctl --quiet --after-cursor %s' % self.cursor
                log_diff = process.system_output(cmd, verbose=False)
                yield log_diff
            except Exception as detail:  # pylint: disable=W0703
                log.debug("Journalctl collection failed: %s", detail)


class LogWatcher(Collectible):

    """
    Keep track of the contents of a log file in another compressed file.

    This object is normally used to track contents of the system log
    (/var/log/messages), and the outputs are gzipped since they can be
    potentially large, helping to save space.

    :param path: Path to the log file.
    :param log_path: Basename of the file where output is logged (optional).
    """

    def __init__(self, path, log_path=None):
        if not log_path:
            log_path = os.path.basename(path) + ".gz"
        else:
            log_path += ".gz"

        super(LogWatcher, self).__init__(log_path)
        self.path = path
        self.size = 0
        self.inode = 0
        try:
            stat = os.stat(path)
            self.size = stat.st_size
            self.inode = stat.st_ino
        except (IOError, OSError):
            log.debug("Not logging %s (lack of permissions)", self.path)

    def __repr__(self):
        r = "LogWatcher(%r, %r)"
        r %= (self.path, self.log_path)
        return r

    def __eq__(self, other):
        if isinstance(other, LogWatcher):
            return (self.path, self.log_path) == (other.path, other.log_path)
        elif isinstance(other, Collectible):
            return False
        return NotImplemented

    def __hash__(self):
        return hash((self.path, self.log_path, LogWatcher))

    def collect(self):
        """
        Collect all of the new data present in the log file.
        :raise CollectibleException
        """
        bytes_to_skip = 0
        current_stat = os.stat(self.path)
        current_inode = current_stat.st_ino
        current_size = current_stat.st_size
        if current_inode == self.inode:
            bytes_to_skip = self.size

        self.inode = current_inode
        self.size = current_size
        try:
            yield from self._read_file(self.path, bytes_to_skip)
        except (IOError, OSError):
            log.debug("Not logging %s (lack of permissions)", self.path)


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
        self.sysinfo_files = {}

        for collectible in ['commands', 'files', 'fail_commands', 'fail_files']:
            tmp_file = self.config.get(
                'sysinfo.collectibles.%s' % collectible)
            if os.path.isfile(tmp_file):
                log.info('%s configured by file: %s', collectible.title(),
                         tmp_file)
                self.sysinfo_files[collectible] = genio.read_all_lines(
                    tmp_file)
            else:
                log.debug('File %s does not exist.', tmp_file)
                self.sysinfo_files[collectible] = []

            if 'fail_' in collectible:
                list1 = self.sysinfo_files[collectible]
                list2 = self.sysinfo_files[collectible.split('_')[1]]
                self.sysinfo_files[collectible] = [
                    tmp for tmp in list1 if tmp not in list2]

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
                return LogWatcher(logpath)
        raise ValueError("System log file not found (looked for %s)" %
                         logpaths)

    def _set_collectibles(self):
        timeout = self.config.get('sysinfo.collect.commands_timeout')
        locale = self.config.get('sysinfo.collect.locale')
        if self.profiler:
            for cmd in self.sysinfo_files["profilers"]:
                self.start_collectibles.add(Daemon(cmd, locale=locale))

        for cmd in self.sysinfo_files["commands"]:
            self.start_collectibles.add(Command(cmd, timeout=timeout,
                                                locale=locale))
            self.end_collectibles.add(Command(cmd, timeout=timeout,
                                              locale=locale))

        for fail_cmd in self.sysinfo_files["fail_commands"]:
            self.end_fail_collectibles.add(Command(fail_cmd, timeout=timeout,
                                                   locale=locale))

        for filename in self.sysinfo_files["files"]:
            self.start_collectibles.add(Logfile(filename))
            self.end_collectibles.add(Logfile(filename))

        for fail_filename in self.sysinfo_files["fail_files"]:
            self.end_fail_collectibles.add(Logfile(fail_filename))

        self.end_collectibles.add(JournalctlWatcher())

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
            if isinstance(log_hook, Daemon):  # log daemons in profile directory
                log_hook.run()
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
            if isinstance(log_hook, Daemon):
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
