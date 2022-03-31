""" Provides utilities to carry out an SSH session.

Example of use:

.. code-block:: python

    from avocado.utils import ssh

    with ssh.Session(host, user='root', key='/path/to/file') as session:
        result = session.cmd('ls')
        if result.exit_status == 0:
            print(result.stdout_text)
"""
import os
import shlex
import stat
import subprocess
import sys
import tempfile

from avocado.utils import path as path_utils
from avocado.utils import process

try:
    #: The SSH client binary to use, if one is found in the system
    SSH_CLIENT_BINARY = path_utils.find_command('ssh')
except path_utils.CmdNotFoundError:
    SSH_CLIENT_BINARY = None


class NWException(Exception):
    """
    Base Exception Class for all exceptions
    """


class Session:
    """
    Represents an SSH session to a remote system, for the purpose of
    executing commands remotely.

    :class:`Session` is also a context manager. On entering the context
    it tries to establish the connection, therefore on exiting that
    connection is closed.
    """

    DEFAULT_OPTIONS = (('StrictHostKeyChecking', 'no'),
                       ('UpdateHostKeys', 'no'),
                       ('ControlPath', '~/.ssh/avocado-master-%r@%h:%p'))

    MASTER_OPTIONS = (('ControlMaster', 'yes'),
                      ('ControlPersist', 'yes'))

    def __init__(self, host, port=None, user=None, key=None, password=None):
        """
        :param host: a host name or IP address
        :type host: str
        :param port: port number
        :type port: int
        :param user: the name of the remote user
        :type user: str
        :param key: path to a key for authentication purpose
        :type key: str
        :param password: password for authentication purpose
        :type password: str
        """
        self.host = host
        self.port = port
        self.user = user
        self.key = key
        self.password = password
        self._connection = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.quit()

    @staticmethod
    def _dash_o_opts_to_str(opts):
        """
        Transforms tuples into options that should be given by "-o Key=Val"
        """
        return " ".join([f"-o '{_[0]}={_[1]}'" for _ in opts])

    def _ssh_cmd(self, dash_o_opts=(), opts=(), command=''):
        cmd = self._dash_o_opts_to_str(dash_o_opts)
        if self.user is not None:
            cmd += f" -l {self.user}"
            if self.key is not None:
                cmd += f" -i {self.key}"
        if self.port is not None:
            cmd += f" -p {self.port}"
        cmd = (f"{SSH_CLIENT_BINARY} {cmd} {' '.join(opts)} "
               f"{self.host} '{command}'")
        return cmd

    def _master_connection(self):
        options = self.DEFAULT_OPTIONS + self.MASTER_OPTIONS
        options += (('PubkeyAuthentication', 'yes' if self.key else 'no'),)
        if self.password is None:
            options += (('PasswordAuthentication', 'no'),)
        else:
            options += (('PasswordAuthentication', 'yes'),
                        ('NumberOfPasswordPrompts', '1'),)
        return self._ssh_cmd(options, ('-T', '-n'))

    def _create_ssh_askpass(self):
        """
        Writes a simple program that complies with SSH_ASKPASS

        This basically writes to stdout the password given
        """
        script = f"#!{sys.executable}\nprint('{self.password}')"
        fd, path = tempfile.mkstemp()
        os.write(fd, script.encode())
        os.fchmod(fd, stat.S_IRUSR | stat.S_IXUSR)
        os.close(fd)
        return path

    def _master_command(self, command):
        cmd = self._ssh_cmd(self.DEFAULT_OPTIONS, ('-O', command))
        result = process.run(cmd, ignore_status=True)
        return result.exit_status == 0

    def _check(self):
        return self._master_command('check')

    def cleanup_master(self):
        """Removes master file if exists."""
        if self.control_master:
            os.unlink(self.control_master)

    def connect(self):
        """
        Establishes the connection to the remote endpoint

        On this implementation, it means creating the master connection,
        which is a process that will live while and be used for subsequent
        commands.

        :returns: whether the connection is successfully established
        :rtype: bool
        """
        if SSH_CLIENT_BINARY is None:
            return False

        if not self._check():
            cmd = shlex.split(self._master_connection())
            if self.password is not None:
                ssh_askpass_path = self._create_ssh_askpass()
                env = {'DISPLAY': 'FAKE_VALUE_TO_SATISFY_SSH',
                       'SSH_ASKPASS': ssh_askpass_path}
                # pylint: disable=W1509
                master = subprocess.Popen(cmd,
                                          stdin=subprocess.DEVNULL,
                                          stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL,
                                          env=env,
                                          preexec_fn=os.setsid)
            else:
                master = subprocess.Popen(cmd,
                                          stdin=subprocess.DEVNULL,
                                          stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL)

            master.wait()
            if self.password is not None:
                os.unlink(ssh_askpass_path)
            if not master.returncode == 0:
                return False
            self._connection = master
        return self._check()

    @property
    def control_master(self):
        control = f"~/.ssh/avocado-master-{self.user}@{self.host}:{self.port}"
        control = os.path.expanduser(control)
        if os.path.exists(control):
            return control

    def get_raw_ssh_command(self, command):
        """
        Returns the raw command that will be executed locally

        This should only be used if you need to interact with the ssh
        subprocess, and most users will *NOT* need to.  Try to use the
        :meth:`cmd` method instead.

        :param command: the command to execute over the SSH session
        :type command: str
        :returns: The raw SSH command, that can be executed locally for
                  the execution of a remote command.
        :rtype: str
        """
        return self._ssh_cmd(self.DEFAULT_OPTIONS, ('-q', ), command)

    def cmd(self, command, ignore_status=True):
        """
        Runs a command over the SSH session

        :param command: the command to execute over the SSH session
        :type command: str
        :param ignore_status: Whether to check the operation failed or not. If
                              set to False then it raises an
                              :class:`avocado.utils.process.CmdError` exception
                              in case of either the command or ssh connection
                              returned with exit status other than zero.
        :type ignore_status: bool
        :returns: The command result object.
        :rtype: A :class:`avocado.utils.process.CmdResult` instance.
        """
        try:
            return process.run(self.get_raw_ssh_command(command),
                               ignore_status=ignore_status)
        except process.CmdError as exc:
            if exc.result.exit_status == 255:
                exc.additional_text = 'SSH connection failed'
            else:
                exc.additional_text = f"Command '{command}' failed"
                exc.stderr = exc.result.stderr
                exc.stdout = exc.result.stdout
            raise exc

    def quit(self):
        """
        Attempts to gracefully end the session, by finishing the master process

        :returns: if closing the session was successful or not
        :rtype: bool
        """
        return self._master_command('exit')

    def copy_files(self, source, destination, recursive=False):
        """
        Copy Files to and from remote through scp session.

        :param source: Source file
        :type: str
        :param destination: Destination file location
        :type: str
        :param recursive: Scp option for copy file. if set to True
                          copy files inside directory recursively.
        :type: bool
        :returns: True if success and an exception if not.
        :rtype: bool
        """
        try:
            cmd = path_utils.find_command('scp')
        except path_utils.CmdNotFoundError as exc:
            raise exc
        options = list(self.DEFAULT_OPTIONS)
        if self.user is not None:  # Prevent failure from unspecified user
            options.append(("User", self.user))
        options = self._dash_o_opts_to_str(options)
        if recursive:
            options += ' -r'
        options += f" {source} {destination}"
        try:
            result = process.run(f"{cmd} {options}",
                                 ignore_status=True)
            return result.exit_status == 0
        except process.CmdError as exc:
            raise NWException(f"failed to copy file {exc}")
