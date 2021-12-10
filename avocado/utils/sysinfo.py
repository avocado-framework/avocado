# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2021
# Authors: Jan Richter <jarichte@redhat.com>
#          John Admanski <jadmanski@google.com>

import json
import os
import shlex
import subprocess
import tempfile
from abc import ABC, abstractmethod

from avocado.utils import astring, process

DATA_SIZE = 200000


class CollectibleException(Exception):
    """
    Base exception for all collectible errors.
    """


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
                raise CollectibleException("Not logging %s (lack of "
                                           "permissions)" % self.path)
        else:
            raise CollectibleException("Not logging %s (file not found)" %
                                       self.path)


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
                                 shell=True,
                                 env=env)
            yield result.stdout
        except FileNotFoundError as exc_fnf:
            raise CollectibleException("Not logging '%s' (command '%s' was not "
                                       "found)" % (self.cmd, exc_fnf.filename))
        except Exception as exc:  # pylint: disable=W0703
            raise CollectibleException('Could not execute "%s": %s' %
                                       (self.cmd, exc))


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
        except OSError as os_err:
            raise CollectibleException('Could not execute "%s": %s' % (self.cmd,
                                                                       os_err))

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
                raise OSError("Daemon process '%s' (pid %d) terminated"
                              " abnormally (code %d)" % (self.cmd,
                                                         self.daemon_process.pid,
                                                         retcode))


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
            raise CollectibleException("Journalctl collection failed: %s" %
                                       detail)

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
                raise CollectibleException("Journalctl collection failed: %s" %
                                           detail)


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
            raise CollectibleException("Not logging %s (lack of permissions)" %
                                       self.path)

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
            raise CollectibleException("Not logging %s (lack of permissions)" %
                                       self.path)
