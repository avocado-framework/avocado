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

from . import output
from .settings import settings
from ..utils import astring
from ..utils import genio
from ..utils import process
from ..utils import software_manager
from ..utils import path as utils_path

log = logging.getLogger("avocado.sysinfo")


class Collectible(object):

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
        if "PATH" not in env:
            env["PATH"] = "/usr/bin:/bin"
        locale = settings.get_value("sysinfo.collect", "locale", str, None)
        if locale:
            env["LC_ALL"] = locale
        timeout = settings.get_value("sysinfo.collect", "commands_timeout",
                                     int, -1)
        # the sysinfo configuration supports negative or zero integer values
        # but the avocado.utils.process APIs define no timeouts as "None"
        if int(timeout) <= 0:
            timeout = None
        result = process.run(self.cmd,
                             timeout=timeout,
                             verbose=False,
                             ignore_status=True,
                             allow_output_check='combined',
                             shell=True,
                             env=env)
        logf_path = os.path.join(logdir, self.logf)
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
        if "PATH" not in env:
            env["PATH"] = "/usr/bin:/bin"
        locale = settings.get_value("sysinfo.collect", "locale", str, None)
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

    def _get_cursor(self):
        try:
            cmd = 'journalctl --quiet --lines 1 --output json'
            result = process.system_output(cmd, verbose=False)
            last_record = json.loads(astring.to_text(result, "utf-8"))
            return last_record['__CURSOR']
        except Exception as detail:
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
            except Exception as detail:
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
        except Exception as detail:
            log.error("Log file %s collection failed: %s", self.path, detail)


class SysInfo(object):

    """
    Log different system properties at some key control points:

    * start_job
    * start_test
    * end_test
    * end_job
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
        if basedir is None:
            basedir = utils_path.init_dir('sysinfo')
        self.basedir = basedir

        self._installed_pkgs = None
        if log_packages is None:
            self.log_packages = settings.get_value('sysinfo.collect',
                                                   'installed_packages',
                                                   key_type='bool',
                                                   default=False)
        else:
            self.log_packages = log_packages

        commands_file = settings.get_value('sysinfo.collectibles',
                                           'commands',
                                           key_type='path',
                                           default='')

        if os.path.isfile(commands_file):
            log.info('Commands configured by file: %s', commands_file)
            self.commands = genio.read_all_lines(commands_file)
        else:
            log.debug('File %s does not exist.', commands_file)
            self.commands = []

        files_file = settings.get_value('sysinfo.collectibles',
                                        'files',
                                        key_type='path',
                                        default='')
        if os.path.isfile(files_file):
            log.info('Files configured by file: %s', files_file)
            self.files = genio.read_all_lines(files_file)
        else:
            log.debug('File %s does not exist.', files_file)
            self.files = []

        if profiler is None:
            self.profiler = settings.get_value('sysinfo.collect',
                                               'profiler',
                                               key_type='bool',
                                               default=False)
        else:
            self.profiler = profiler

        profiler_file = settings.get_value('sysinfo.collectibles',
                                           'profilers',
                                           key_type='path',
                                           default='')
        if os.path.isfile(profiler_file):
            self.profilers = genio.read_all_lines(profiler_file)
            log.info('Profilers configured by file: %s', profiler_file)
            if not self.profilers:
                self.profiler = False

            if self.profiler is False:
                if not self.profilers:
                    log.info('Profiler disabled: no profiler'
                             ' commands configured')
                else:
                    log.info('Profiler disabled')
        else:
            log.debug('File %s does not exist.', profiler_file)
            self.profilers = []

        self.start_job_collectibles = set()
        self.end_job_collectibles = set()

        self.start_test_collectibles = set()
        self.end_test_collectibles = set()

        self.hook_mapping = {'start_job': self.start_job_collectibles,
                             'end_job': self.end_job_collectibles,
                             'start_test': self.start_test_collectibles,
                             'end_test': self.end_test_collectibles}

        self.pre_dir = utils_path.init_dir(self.basedir, 'pre')
        self.post_dir = utils_path.init_dir(self.basedir, 'post')
        self.profile_dir = utils_path.init_dir(self.basedir, 'profile')

        self._set_collectibles()

    def _get_syslog_watcher(self):
        logpaths = ["/var/log/messages",
                    "/var/log/syslog",
                    "/var/log/system.log"]
        for logpath in logpaths:
            if os.path.exists(logpath):
                return LogWatcher(logpath)
        raise ValueError("System log file not found (looked for %s)" %
                         logpaths)

    def _set_collectibles(self):
        add_per_test = settings.get_value("sysinfo.collect", "per_test",
                                          bool, None)
        if self.profiler:
            for cmd in self.profilers:
                self.start_job_collectibles.add(Daemon(cmd))
                if add_per_test:
                    self.start_test_collectibles.add(Daemon(cmd))

        for cmd in self.commands:
            self.start_job_collectibles.add(Command(cmd))
            self.end_job_collectibles.add(Command(cmd))
            if add_per_test:
                self.start_test_collectibles.add(Command(cmd))
                self.end_test_collectibles.add(Command(cmd))

        for filename in self.files:
            self.start_job_collectibles.add(Logfile(filename))
            self.end_job_collectibles.add(Logfile(filename))
            if add_per_test:
                self.start_test_collectibles.add(Logfile(filename))
                self.end_test_collectibles.add(Logfile(filename))

        # As the system log path is not standardized between distros,
        # we have to probe and find out the correct path.
        try:
            self.end_test_collectibles.add(self._get_syslog_watcher())
        except ValueError as details:
            log.info(details)

        self.end_test_collectibles.add(JournalctlWatcher())

    def _get_collectibles(self, hook):
        collectibles = self.hook_mapping.get(hook)
        if collectibles is None:
            raise ValueError('Incorrect hook, valid hook names: %s' %
                             self.hook_mapping.keys())
        return collectibles

    def add_cmd(self, cmd, hook):
        """
        Add a command collectible.

        :param cmd: Command to log.
        :param hook: In which hook this cmd should be logged (start job, end
                     job).
        """
        collectibles = self._get_collectibles(hook)
        collectibles.add(Command(cmd))

    def add_file(self, filename, hook):
        """
        Add a system file collectible.

        :param filename: Path to the file to be logged.
        :param hook: In which hook this file should be logged (start job, end
                     job).
        """
        collectibles = self._get_collectibles(hook)
        collectibles.add(Logfile(filename))

    def add_watcher(self, filename, hook):
        """
        Add a system file watcher collectible.

        :param filename: Path to the file to be logged.
        :param hook: In which hook this watcher should be logged
                    (start job, end job).
        """
        collectibles = self._get_collectibles(hook)
        collectibles.add(LogWatcher(filename))

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

    def start_job_hook(self):
        """
        Logging hook called whenever a job starts.
        """
        for log_hook in self.start_job_collectibles:
            if isinstance(log_hook, Daemon):  # log daemons in profile directory
                log_hook.run(self.profile_dir)
            else:
                log_hook.run(self.pre_dir)

        if self.log_packages:
            self._log_installed_packages(self.pre_dir)

    def end_job_hook(self):
        """
        Logging hook called whenever a job finishes.
        """
        for log_hook in self.end_job_collectibles:
            log_hook.run(self.post_dir)
        # Stop daemon(s) started previously
        for log_hook in self.start_job_collectibles:
            if isinstance(log_hook, Daemon):
                log_hook.stop()

        if self.log_packages:
            self._log_modified_packages(self.post_dir)

    def start_test_hook(self):
        """
        Logging hook called before a test starts.
        """
        for log_hook in self.start_test_collectibles:
            if isinstance(log_hook, Daemon):  # log daemons in profile directory
                log_hook.run(self.profile_dir)
            else:
                log_hook.run(self.pre_dir)

        if self.log_packages:
            self._log_installed_packages(self.pre_dir)

    def end_test_hook(self):
        """
        Logging hook called after a test finishes.
        """
        for log_hook in self.end_test_collectibles:
            log_hook.run(self.post_dir)
        # Stop daemon(s) started previously
        for log_hook in self.start_test_collectibles:
            if isinstance(log_hook, Daemon):
                log_hook.stop()

        if self.log_packages:
            self._log_modified_packages(self.post_dir)


def collect_sysinfo(args):
    """
    Collect sysinfo to a base directory.

    :param args: :class:`argparse.Namespace` object with command line params.
    """
    output.add_log_handler(log.name)

    basedir = args.sysinfodir
    if not basedir:
        cwd = os.getcwd()
        timestamp = time.strftime('%Y-%m-%d-%H.%M.%S')
        basedir = os.path.join(cwd, 'sysinfo-%s' % timestamp)

    sysinfo_logger = SysInfo(basedir=basedir)
    sysinfo_logger.start_job_hook()
    sysinfo_logger.end_job_hook()
    log.info("Logged system information to %s", basedir)
