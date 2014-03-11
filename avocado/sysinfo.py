import gzip
import logging
import os
import shutil
import subprocess

from avocado import utils
from avocado.linux import software_manager

log = logging.getLogger("avocado.utils")


_DEFAULT_COMMANDS_START_JOB = ["df -mP",
                               "dmesg -c",
                               "uname -a",
                               "lspci -vvnn",
                               "gcc --version",
                               "ld --version",
                               "mount",
                               "hostname",
                               "uptime",
                               "dmidecode"]
_DEFAULT_COMMANDS_END_JOB = []

_DEFAULT_FILES_START_JOB = ["/proc/cmdline",
                            "/proc/mounts",
                            "/proc/pci",
                            "/proc/meminfo",
                            "/proc/slabinfo",
                            "/proc/version",
                            "/proc/cpuinfo",
                            "/proc/modules",
                            "/proc/interrupts",
                            "/proc/partitions"]

_DEFAULT_FILES_END_JOB = []

_DEFAULT_COMMANDS_START_TEST = []

_DEFAULT_COMMANDS_END_TEST = []

_DEFAULT_FILES_START_TEST = []

_DEFAULT_FILES_END_TEST = []

_DEFAULT_COMMANDS_START_ITERATION = []
_DEFAULT_COMMANDS_END_ITERATION = ["/proc/schedstat",
                                   "/proc/meminfo",
                                   "/proc/slabinfo",
                                   "/proc/interrupts",
                                   "/proc/buddyinfo"]

_DEFAULT_FILES_START_ITERATION = []
_DEFAULT_FILES_END_ITERATION = ["/proc/schedstat",
                                "/proc/meminfo",
                                "/proc/slabinfo",
                                "/proc/interrupts",
                                "/proc/buddyinfo"]


class Loggable(object):

    """
    Abstract class for representing all things "loggable" by sysinfo.
    """

    def __init__(self, logf):
        self.logf = logf

    def readline(self, logdir):
        path = os.path.join(logdir, self.logf)
        if os.path.exists(path):
            return utils.misc.read_one_line(path)
        else:
            return ""


class Logfile(Loggable):

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
        if os.path.exists(self.path):
            try:
                shutil.copyfile(self.path, os.path.join(logdir, self.logf))
            except IOError:
                log.info("Not logging %s (lack of permissions)", self.path)


class Command(Loggable):

    def __init__(self, cmd, logf=None, compress_log=False):
        if not logf:
            logf = cmd.replace(" ", "_")
        super(Command, self).__init__(logf)
        self.cmd = cmd
        self._compress_log = compress_log

    def __repr__(self):
        r = "sysinfo.Command(%r, %r, %r)"
        r %= (self.cmd, self.logf)
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
        env = os.environ.copy()
        if "PATH" not in env:
            env["PATH"] = "/usr/bin:/bin"
        logf_path = os.path.join(logdir, self.logf)
        stdin = open(os.devnull, "r")
        stderr = open(os.devnull, "w")
        stdout = open(logf_path, "w")
        try:
            subprocess.call(self.cmd, stdin=stdin, stdout=stdout,
                            stderr=stderr, shell=True, env=env)
        finally:
            for f in (stdin, stdout, stderr):
                f.close()
            if self._compress_log and os.path.exists(logf_path):
                utils.process.run('gzip -9 "%s"' % logf_path,
                                  ignore_status=True,
                                  verbose=False)


class LogWatcher(Loggable):

    """
    Keep track of the contents of a log file in another compressed file.

    This object is normally used to track contents of the system log
    (/var/log/messages), and the outputs are gzipped since they can be
    potentially large, helping to save space.
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
            log.info("Not logging %s (lack of permissions)", self.path)

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
                    # Read data in managable chunks rather than all at once.
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
            log.info("Not logging %s (lack of permissions)", self.path)
        except Exception, e:
            log.info("Log file %s collection failed: %s", self.path, e)


class SysInfo(object):

    """
    Log different system properties at some key control points:

    * start_job
    * start_test
    * start_iteration
    * end_iteration
    * end_test
    * end_job
    """

    def __init__(self, basedir=None, log_packages=False):
        """
        Set sysinfo loggables.

        :param basedir: Base log dir where sysinfo files will be located.
        :param log_packages: Whether to log system packages (optional because
                logging packages is a costly operation).
        """
        if basedir is None:
            basedir = os.path.join(os.getcwd(), 'sysinfo')

        if not os.path.isdir(basedir):
            os.makedirs(basedir)

        self.basedir = basedir
        self.log_packages = log_packages
        self._installed_pkgs = None

        self.start_job_loggables = set()
        self.end_job_loggables = set()

        self.start_test_loggables = set()
        self.end_test_loggables = set()

        self.start_iteration_loggables = set()
        self.end_iteration_loggables = set()

        self.hook_mapping = {'start_job': self.start_job_loggables,
                             'end_job': self.end_job_loggables,
                             'start_test': self.start_test_loggables,
                             'end_test': self.end_test_loggables,
                             'start_iteration': self.start_iteration_loggables,
                             'end_iteration': self.end_iteration_loggables}

        self._set_loggables()

    def _get_syslog_watcher(self):
        syslog_watcher = None

        logpaths = ["/var/log/messages", "/var/log/syslog"]
        for logpath in logpaths:
            if os.path.exists(logpath):
                syslog_watcher = LogWatcher(logpath)

        if syslog_watcher is None:
            raise ValueError("System log file not found (looked for %s)" %
                             logpaths)

        return syslog_watcher

    def _set_loggables(self):
        for cmd in _DEFAULT_COMMANDS_START_JOB:
            self.start_job_loggables.add(Command(cmd))

        for cmd in _DEFAULT_COMMANDS_END_JOB:
            self.end_job_loggables.add(Command(cmd))

        for filename in _DEFAULT_FILES_START_JOB:
            self.start_job_loggables.add(Logfile(filename))

        for filename in _DEFAULT_FILES_END_JOB:
            self.end_job_loggables.add(Logfile(filename))

        for cmd in _DEFAULT_COMMANDS_START_TEST:
            self.start_job_loggables.add(Command(cmd))

        for cmd in _DEFAULT_COMMANDS_END_TEST:
            self.end_test_loggables.add(Command(cmd))

        # As the system log path is not standardized between distros,
        # we have to probe and find out the correct path.
        self.end_test_loggables.add(self._get_syslog_watcher())

        for filename in _DEFAULT_FILES_START_TEST:
            self.start_test_loggables.add(Logfile(filename))

        for filename in _DEFAULT_FILES_END_TEST:
            self.end_test_loggables.add(Logfile(filename))

        for cmd in _DEFAULT_COMMANDS_START_ITERATION:
            self.start_iteration_loggables.add(Command(cmd))

        for cmd in _DEFAULT_COMMANDS_END_ITERATION:
            self.end_iteration_loggables.add(Command(cmd))

        for filename in _DEFAULT_FILES_START_ITERATION:
            self.start_iteration_loggables.add(Logfile(filename))

        for filename in _DEFAULT_FILES_END_ITERATION:
            self.end_iteration_loggables.add(Logfile(filename))

    def _get_loggables(self, hook):
        loggables = self.hook_mapping.get(hook)
        if loggables is None:
            raise ValueError('Incorrect hook, valid hook names: %s' %
                             self.hook_mapping.keys())
        return loggables

    def add_cmd(self, cmd, hook):
        loggables = self._get_loggables(hook)
        loggables.add(Command(cmd))

    def add_file(self, filename, hook):
        loggables = self._get_loggables(hook)
        loggables.add(Logfile(filename))

    def add_watcher(self, filename, hook):
        loggables = self._get_loggables(hook)
        loggables.add(LogWatcher(filename))

    def _get_installed_packages(self):
        sm = software_manager.SoftwareManager()
        installed_pkgs = sm.list_all()
        self._installed_pkgs = installed_pkgs
        return installed_pkgs

    def _log_installed_packages(self):
        installed_path = os.path.join(self.basedir, "installed_packages")
        installed_packages = "\n".join(self._get_installed_packages()) + "\n"
        utils.misc.write_file(installed_path, installed_packages)

    def _log_modified_packages(self):
        """
        Log any changes to installed packages.
        """
        old_packages = set(self._installed_packages)
        new_packages = set(self._get_installed_packages())
        added_path = os.path.join(self.basedir, "added_packages")
        added_packages = "\n".join(new_packages - old_packages) + "\n"
        utils.misc.write_file(added_path, added_packages)
        removed_path = os.path.join(self.basedir, "removed_packages")
        removed_packages = "\n".join(old_packages - new_packages) + "\n"
        utils.misc.write_file(removed_path, removed_packages)

    def start_job_hook(self):
        """
        Logging hook called whenever a job starts, and again after reboot.
        """
        for log in self.start_job_loggables:
            log.run(self.basedir)

        if self.log_packages:
            self._log_installed_packages()

    def start_test_hook(self):
        """
        Logging hook called before a test starts.
        """
        for log in self.start_test_loggables:
            log.run(self.basedir)

        if self.log_packages:
            self._log_installed_packages()

    def end_test_hook(self):
        """
        Logging hook called after a test finishes.
        """
        for log in self.end_test_loggables:
            log.run(self.basedir)

        if self.log_packages:
            self._log_modified_packages()

    def start_iteration_hook(self):
        """
        Logging hook called before a test iteration
        """
        for log in self.start_iteration_loggables:
            log.run(self.basedir)

    def end_iteration_hook(self, test, iteration=None):
        """
        Logging hook called after a test iteration
        """
        for log in self.end_iteration_loggables:
            log.run(self.basedir)
