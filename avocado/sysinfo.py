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
import logging
import os
import shutil
import time

try:
    import subprocess32 as subprocess
except ImportError:
    import subprocess

from avocado import utils
from avocado.linux import software_manager
from avocado.core import output
from avocado.settings import settings

log = logging.getLogger("avocado.sysinfo")


_DEFAULT_COMMANDS_JOB = ["df -mP",
                         "dmesg -c",
                         "uname -a",
                         "lspci -vvnn",
                         "gcc --version",
                         "ld --version",
                         "mount",
                         "hostname",
                         "uptime",
                         "dmidecode",
                         "ifconfig -a",
                         "brctl show",
                         "ip link",
                         "numactl --hardware show",
                         "lscpu",
                         "fdisk -l"]

_DEFAULT_FILES_JOB = ["/proc/cmdline",
                      "/proc/mounts",
                      "/proc/pci",
                      "/proc/meminfo",
                      "/proc/slabinfo",
                      "/proc/version",
                      "/proc/cpuinfo",
                      "/proc/modules",
                      "/proc/interrupts",
                      "/proc/partitions",
                      "/sys/kernel/debug/sched_features",
                      "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor",
                      "/sys/devices/system/clocksource/clocksource0/current_clocksource"]


class Loggable(object):

    """
    Abstract class for representing all things "loggable" by sysinfo.
    """

    def __init__(self, logf):
        self.logf = logf

    def readline(self, logdir):
        """
        Read one line of the loggable object.

        :param logdir: Path to a log directory.
        """
        path = os.path.join(logdir, self.logf)
        if os.path.exists(path):
            return utils.genio.read_one_line(path)
        else:
            return ""


class Logfile(Loggable):

    """
    Loggable system file.

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
        elif isinstance(other, Loggable):
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


class Command(Loggable):

    """
    Loggable command.

    :param cmd: String with the command.
    :param logf: Basename of the file where output is logged (optional).
    :param compress_logf: Wether to compress the output of the command.
    """

    def __init__(self, cmd, logf=None, compress_log=False):
        if not logf:
            logf = cmd.replace(" ", "_")
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
        elif isinstance(other, Loggable):
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
        logf_path = os.path.join(logdir, self.logf)
        stdin = open(os.devnull, "r")
        stdout = open(logf_path, "w")
        try:
            subprocess.call(self.cmd, stdin=stdin, stdout=stdout,
                            stderr=subprocess.STDOUT, shell=True, env=env)
        finally:
            for f in (stdin, stdout):
                f.close()
            if self._compress_log and os.path.exists(logf_path):
                utils.process.run('gzip -9 "%s"' % logf_path,
                                  ignore_status=True,
                                  verbose=False)


class Daemon(Command):

    """
    Loggable daemon.

    :param cmd: String with the daemon command.
    :param logf: Basename of the file where output is logged (optional).
    :param compress_logf: Wether to compress the output of the command.
    """

    def run(self, logdir):
        """
        Execute the daemon as a subprocess and log its output in logdir.

        :param logdir: Path to a log directory.
        """
        env = os.environ.copy()
        if "PATH" not in env:
            env["PATH"] = "/usr/bin:/bin"
        logf_path = os.path.join(logdir, self.logf)
        stdin = open(os.devnull, "r")
        stdout = open(logf_path, "w")
        self.pipe = subprocess.Popen(self.cmd, stdin=stdin, stdout=stdout,
                                     stderr=subprocess.STDOUT, shell=True, env=env)

    def stop(self):
        """
        Stop daemon execution.
        """
        retcode = self.pipe.poll()
        if retcode is None:
            self.pipe.terminate()
            retcode = self.pipe.wait()
        else:
            log.error("Daemon process '%s' (pid %d) terminated abnormally (code %d)",
                      self.cmd, self.pipe.pid, retcode)
        return retcode


class LogWatcher(Loggable):

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
        elif isinstance(other, Loggable):
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

            in_messages = open(self.path)
            out_messages = gzip.GzipFile(dstpath, "w")
            try:
                in_messages.seek(bytes_to_skip)
                while True:
                    # Read data in manageable chunks rather than all at once.
                    in_data = in_messages.read(200000)
                    if not in_data:
                        break
                    out_messages.write(in_data)
            finally:
                out_messages.close()
                in_messages.close()
        except ValueError, e:
            log.info(e)
        except (IOError, OSError):
            log.debug("Not logging %s (lack of permissions)", self.path)
        except Exception, e:
            log.error("Log file %s collection failed: %s", self.path, e)


class SysInfo(object):

    """
    Log different system properties at some key control points:

    * start_job
    * start_test
    * end_test
    * end_job
    """

    def __init__(self, basedir=None, log_packages=None, profilers=None):
        """
        Set sysinfo loggables.

        :param basedir: Base log dir where sysinfo files will be located.
        :param log_packages: Whether to log system packages (optional because
                             logging packages is a costly operation). If not
                             given explicitly, tries to look in the config
                             files, and if not found, defaults to False.
        :param profilers: Wether to use the profiler. If not given explicitly,
                          tries to look in the config files.
        """
        if basedir is None:
            basedir = utils.path.init_dir('sysinfo')
        self.basedir = basedir

        self._installed_pkgs = None
        if log_packages is None:
            self.log_packages = settings.get_value('sysinfo.collect',
                                                   'installed_packages',
                                                   key_type='bool',
                                                   default=False)
        else:
            self.log_packages = log_packages

        if profilers is None:
            self.profiler = settings.get_value('sysinfo.collect',
                                               'profiler',
                                               key_type='bool',
                                               default=False)
            profiler_commands = settings.get_value('sysinfo.collect',
                                                   'profiler_commands',
                                                   key_type='str',
                                                   default='')
        else:
            self.profiler = True
            profiler_commands = profilers

        self.profiler_commands = [x for x in profiler_commands.split(':') if x.strip()]
        log.info('Profilers declared: %s', self.profiler_commands)
        if not self.profiler_commands:
            self.profiler = False

        if self.profiler is False:
            if not self.profiler_commands:
                log.info('Profiler disabled: no profiler commands configured')
            else:
                log.info('Profiler disabled')

        self.start_job_loggables = set()
        self.end_job_loggables = set()

        self.start_test_loggables = set()
        self.end_test_loggables = set()

        self.hook_mapping = {'start_job': self.start_job_loggables,
                             'end_job': self.end_job_loggables,
                             'start_test': self.start_test_loggables,
                             'end_test': self.end_test_loggables}

        self.pre_dir = utils.path.init_dir(self.basedir, 'pre')
        self.post_dir = utils.path.init_dir(self.basedir, 'post')
        self.profile_dir = utils.path.init_dir(self.basedir, 'profile')

        self._set_loggables()

    def _get_syslog_watcher(self):
        syslog_watcher = None

        logpaths = ["/var/log/messages",
                    "/var/log/syslog",
                    "/var/log/system.log"]
        for logpath in logpaths:
            if os.path.exists(logpath):
                syslog_watcher = LogWatcher(logpath)

        if syslog_watcher is None:
            raise ValueError("System log file not found (looked for %s)" %
                             logpaths)

        return syslog_watcher

    def _set_loggables(self):
        if self.profiler:
            for cmd in self.profiler_commands:
                self.start_job_loggables.add(Daemon(cmd))

        for cmd in _DEFAULT_COMMANDS_JOB:
            self.start_job_loggables.add(Command(cmd))
            self.end_job_loggables.add(Command(cmd))

        for filename in _DEFAULT_FILES_JOB:
            self.start_job_loggables.add(Logfile(filename))
            self.end_job_loggables.add(Logfile(filename))

        # As the system log path is not standardized between distros,
        # we have to probe and find out the correct path.
        try:
            self.end_test_loggables.add(self._get_syslog_watcher())
        except ValueError, details:
            log.info(details)

    def _get_loggables(self, hook):
        loggables = self.hook_mapping.get(hook)
        if loggables is None:
            raise ValueError('Incorrect hook, valid hook names: %s' %
                             self.hook_mapping.keys())
        return loggables

    def add_cmd(self, cmd, hook):
        """
        Add a command loggable.

        :param cmd: Command to log.
        :param hook: In which hook this cmd should be logged (start job, end
                     job).
        """
        loggables = self._get_loggables(hook)
        loggables.add(Command(cmd))

    def add_file(self, filename, hook):
        """
        Add a system file loggable.

        :param filename: Path to the file to be logged.
        :param hook: In which hook this file should be logged (start job, end
                     job).
        """
        loggables = self._get_loggables(hook)
        loggables.add(Logfile(filename))

    def add_watcher(self, filename, hook):
        """
        Add a system file watcher loggable.

        :param filename: Path to the file to be logged.
        :param hook: In which hook this watcher should be logged (start job, end
                     job).
        """
        loggables = self._get_loggables(hook)
        loggables.add(LogWatcher(filename))

    def _get_installed_packages(self):
        sm = software_manager.SoftwareManager()
        installed_pkgs = sm.list_all()
        self._installed_pkgs = installed_pkgs
        return installed_pkgs

    def _log_installed_packages(self, path):
        installed_path = os.path.join(path, "installed_packages")
        installed_packages = "\n".join(self._get_installed_packages()) + "\n"
        utils.genio.write_file(installed_path, installed_packages)

    def _log_modified_packages(self, path):
        """
        Log any changes to installed packages.
        """
        old_packages = set(self._installed_pkgs)
        new_packages = set(self._get_installed_packages())
        added_path = os.path.join(path, "added_packages")
        added_packages = "\n".join(new_packages - old_packages) + "\n"
        utils.genio.write_file(added_path, added_packages)
        removed_path = os.path.join(self.basedir, "removed_packages")
        removed_packages = "\n".join(old_packages - new_packages) + "\n"
        utils.genio.write_file(removed_path, removed_packages)

    def start_job_hook(self):
        """
        Logging hook called whenever a job starts.
        """
        for log in self.start_job_loggables:
            if isinstance(log, Daemon):  # log daemons in profile directory
                log.run(self.profile_dir)
            else:
                log.run(self.pre_dir)

        if self.log_packages:
            self._log_installed_packages(self.pre_dir)

    def end_job_hook(self):
        """
        Logging hook called whenever a job finishes.
        """
        for log in self.end_job_loggables:
            log.run(self.post_dir)
        # Stop daemon(s) started previously
        for log in self.start_job_loggables:
            if isinstance(log, Daemon):
                log.stop()

        if self.log_packages:
            self._log_modified_packages(self.post_dir)

    def start_test_hook(self):
        """
        Logging hook called before a test starts.
        """
        for log in self.start_test_loggables:
            log.run(self.pre_dir)

        if self.log_packages:
            self._log_installed_packages(self.pre_dir)

    def end_test_hook(self):
        """
        Logging hook called after a test finishes.
        """
        for log in self.end_test_loggables:
            log.run(self.post_dir)

        if self.log_packages:
            self._log_modified_packages(self.post_dir)


def collect_sysinfo(args):
    """
    Collect sysinfo to a base directory.

    :param args: :class:`argparse.Namespace` object with command line params.
    """
    output.add_console_handler(log)

    basedir = args.sysinfodir
    if not basedir:
        cwd = os.getcwd()
        timestamp = time.strftime('%Y-%m-%d-%H.%M.%S')
        basedir = os.path.join(cwd, 'sysinfo-%s' % timestamp)

    sysinfo_logger = SysInfo(basedir=basedir, log_packages=True)
    sysinfo_logger.start_job_hook()
    sysinfo_logger.end_job_hook()
    log.info("Logged system information to %s", basedir)
