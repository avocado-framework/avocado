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

import gzip
import json
import logging
import os
import shlex
import shutil
import subprocess
import time

from ..utils import astring, genio
from ..utils import path as utils_path
from ..utils import process, software_manager
from . import output
from .settings import settings

log = logging.getLogger("avocado.sysinfo")


class Collectible:

    """
    Abstract class for representing collectibles by sysinfo.
    """

    def __init__(self, logf):
        self.logf = astring.string_to_safe_path(logf)

    def readline(self, logdir):
        """
        Read one line of the collectible object.

        :param logdir: Path to a log directory.
        """
        path = os.path.join(logdir, self.logf)
        if os.path.exists(path):
            return genio.read_one_line(path)
        else:
            return ""


class Logfile(Collectible):

    """
    Collectible system file.

    :param path: Path to the log file.
    :param logf: Basename of the file where output is logged (optional).
    """

    def __init__(self, path, logf=None):
        if not logf:
            logf = os.path.basename(path)
        super(Logfile, self).__init__(logf)
        self.path = path

    def __repr__(self):
        r = "sysinfo.Logfile(%r, %r)"
        r %= (self.path, self.logf)
        return r

    def __eq__(self, other):
        if isinstance(other, Logfile):
            return (self.path, self.logf) == (other.path, other.logf)
        elif isinstance(other, Collectible):
            return False
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        return hash((self.path, self.logf))

    def run(self, logdir):
        """
        Copy the log file to the appropriate log dir.

        :param logdir: Log directory which the file is going to be copied to.
        """
        if os.path.exists(self.path):
            config = settings.as_dict()
            if config.get('sysinfo.collect.optimize') and logdir.endswith('post'):
                pre_file = os.path.join(os.path.dirname(logdir), 'pre',
                                        self.logf)
                if os.path.isfile(pre_file):
                    with open(self.path) as f1, open(pre_file) as f2:
                        if f1.read() == f2.read():
                            log.debug("Not logging %s (no change detected)",
                                      self.path)
                            return
            try:
                shutil.copyfile(self.path, os.path.join(logdir, self.logf))
            except IOError:
                log.debug("Not logging %s (lack of permissions)", self.path)
        else:
            log.debug("Not logging %s (file does not exist)", self.path)


class Command(Collectible):

    """
    Collectible command.

    :param cmd: String with the command.
    :param logf: Basename of the file where output is logged (optional).
    :param compress_log: Whether to compress the output of the command.
    """

    def __init__(self, cmd, logf=None, compress_log=False):
        if not logf:
            logf = cmd
        super(Command, self).__init__(logf)
        self.cmd = cmd
        self._compress_log = compress_log

    def __repr__(self):
        r = "sysinfo.Command(%r, %r, %r)"
        r %= (self.cmd, self.logf, self._compress_log)
        return r

    def __eq__(self, other):
        if isinstance(other, Command):
            return (self.cmd, self.logf) == (other.cmd, other.logf)
        elif isinstance(other, Collectible):
            return False
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        return hash((self.cmd, self.logf))

    def run(self, logdir):
        """
        Execute the command as a subprocess and log its output in logdir.

        :param logdir: Path to a log directory.
        """
        env = os.environ.copy()
        config = settings.as_dict()
        if "PATH" not in env:
            env["PATH"] = "/usr/bin:/bin"
        locale = config.get("sysinfo.collect.locale")
        if locale:
            env["LC_ALL"] = locale
        timeout = config.get('sysinfo.collect.commands_timeout')
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
            log.debug("Not logging '%s' (command '%s' was not found)", self.cmd,
                      exc_fnf.filename)
            return
        except Exception as exc:  # pylint: disable=W0703
            log.warning('Could not execute "%s": %s', self.cmd, exc)
            return
        logf_path = os.path.join(logdir, self.logf)
        if config.get('sysinfo.collect.optimize') and logdir.endswith('post'):
            pre_file = os.path.join(os.path.dirname(logdir), 'pre', self.logf)
            if os.path.isfile(pre_file):
                with open(pre_file, 'rb') as f1:
                    if f1.read() == result.stdout:
                        log.debug("Not logging %s (no change detected)",
                                  self.cmd)
                        return
        if self._compress_log:
            with gzip.GzipFile(logf_path, 'wb') as logf:
                logf.write(result.stdout)
        else:
            with open(logf_path, 'wb') as logf:
                logf.write(result.stdout)


class Daemon(Command):

    """
    Collectible daemon.

    :param cmd: String with the daemon command.
    :param logf: Basename of the file where output is logged (optional).
    :param compress_log: Whether to compress the output of the command.
    """

    def __init__(self, *args, **kwargs):
        super(Daemon, self).__init__(*args, **kwargs)
        self.daemon_process = None

    def run(self, logdir):
        """
        Execute the daemon as a subprocess and log its output in logdir.

        :param logdir: Path to a log directory.
        """
        env = os.environ.copy()
        config = settings.as_dict()
        if "PATH" not in env:
            env["PATH"] = "/usr/bin:/bin"
        locale = config.get("sysinfo.collect.locale")
        if locale:
            env["LC_ALL"] = locale
        logf_path = os.path.join(logdir, self.logf)
        stdin = open(os.devnull, "r")
        stdout = open(logf_path, "w")

        try:
            self.daemon_process = subprocess.Popen(shlex.split(self.cmd),
                                                   stdin=stdin, stdout=stdout,
                                                   stderr=subprocess.STDOUT,
                                                   shell=False, env=env)
        except OSError:
            log.debug("Not logging  %s (command could not be run)", self.cmd)

    def stop(self):
        """
        Stop daemon execution.
        """
        if self.daemon_process is not None:
            retcode = self.daemon_process.poll()
            if retcode is None:
                process.kill_process_tree(self.daemon_process.pid)
                retcode = self.daemon_process.wait()
            else:
                log.error("Daemon process '%s' (pid %d) "
                          "terminated abnormally (code %d)",
                          self.cmd, self.daemon_process.pid, retcode)
            return retcode


class JournalctlWatcher(Collectible):

    """
    Track the content of systemd journal into a compressed file.

    :param logf: Basename of the file where output is logged (optional).
    """

    def __init__(self, logf=None):
        if not logf:
            logf = 'journalctl.gz'

        super(JournalctlWatcher, self).__init__(logf)
        self.cursor = self._get_cursor()

    @staticmethod
    def _get_cursor():
        try:
            cmd = 'journalctl --quiet --lines 1 --output json'
            result = process.system_output(cmd, verbose=False)
            last_record = json.loads(astring.to_text(result, "utf-8"))
            return last_record['__CURSOR']
        except Exception as detail:  # pylint: disable=W0703
            log.debug("Journalctl collection failed: %s", detail)

    def run(self, logdir):
        if self.cursor:
            try:
                cmd = 'journalctl --quiet --after-cursor %s' % self.cursor
                log_diff = process.system_output(cmd, verbose=False)
                dstpath = os.path.join(logdir, self.logf)
                with gzip.GzipFile(dstpath, "wb") as out_journalctl:
                    out_journalctl.write(log_diff)
            except IOError:
                log.debug("Not logging journalctl (lack of permissions): %s",
                          dstpath)
            except Exception as detail:  # pylint: disable=W0703
                log.debug("Journalctl collection failed: %s", detail)


class LogWatcher(Collectible):

    """
    Keep track of the contents of a log file in another compressed file.

    This object is normally used to track contents of the system log
    (/var/log/messages), and the outputs are gzipped since they can be
    potentially large, helping to save space.

    :param path: Path to the log file.
    :param logf: Basename of the file where output is logged (optional).
    """

    def __init__(self, path, logf=None):
        if not logf:
            logf = os.path.basename(path) + ".gz"
        else:
            logf += ".gz"

        super(LogWatcher, self).__init__(logf)
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
        r = "sysinfo.LogWatcher(%r, %r)"
        r %= (self.path, self.logf)
        return r

    def __eq__(self, other):
        if isinstance(other, Logfile):
            return (self.path, self.logf) == (other.path, other.logf)
        elif isinstance(other, Collectible):
            return False
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        return hash((self.path, self.logf))

    def run(self, logdir):
        """
        Log all of the new data present in the log file.
        """
        try:
            dstname = self.logf
            dstpath = os.path.join(logdir, dstname)

            bytes_to_skip = 0
            current_stat = os.stat(self.path)
            current_inode = current_stat.st_ino
            current_size = current_stat.st_size
            if current_inode == self.inode:
                bytes_to_skip = self.size

            self.inode = current_inode
            self.size = current_size

            with open(self.path, "rb") as in_messages:
                with gzip.GzipFile(dstpath, "wb") as out_messages:
                    in_messages.seek(bytes_to_skip)
                    while True:
                        # Read data in manageable chunks rather than
                        # all at once.
                        in_data = in_messages.read(200000)
                        if not in_data:
                            break
                        out_messages.write(in_data)
        except ValueError as detail:
            log.info(detail)
        except (IOError, OSError):
            log.debug("Not logging %s (lack of permissions)", self.path)
        except Exception as detail:  # pylint: disable=W0703
            log.error("Log file %s collection failed: %s", self.path, detail)


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
        if self.profiler:
            for cmd in self.sysinfo_files["profilers"]:
                self.start_collectibles.add(Daemon(cmd))

        for cmd in self.sysinfo_files["commands"]:
            self.start_collectibles.add(Command(cmd))
            self.end_collectibles.add(Command(cmd))

        for fail_cmd in self.sysinfo_files["fail_commands"]:
            self.end_fail_collectibles.add(Command(fail_cmd))

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

    def start(self):
        """Log all collectibles at the start of the event."""
        os.environ['AVOCADO_SYSINFODIR'] = self.pre_dir
        for log_hook in self.start_collectibles:
            if isinstance(log_hook, Daemon):  # log daemons in profile directory
                log_hook.run(self.profile_dir)
            else:
                log_hook.run(self.pre_dir)

        if self.log_packages:
            self._log_installed_packages(self.pre_dir)

    def end(self, status=""):
        """
        Logging hook called whenever a job finishes.
        """
        os.environ['AVOCADO_SYSINFODIR'] = self.post_dir
        for log_hook in self.end_collectibles:
            log_hook.run(self.post_dir)

        if status == "FAIL":
            for log_hook in self.end_fail_collectibles:
                log_hook.run(self.post_dir)

        # Stop daemon(s) started previously
        for log_hook in self.start_collectibles:
            if isinstance(log_hook, Daemon):
                log_hook.stop()

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
