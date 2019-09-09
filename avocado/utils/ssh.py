from . import process


class Session:
    """
    Represents an SSH session to a remote system, for the purpose of
    executing commands remotely.
    """

    DEFAULT_OPTIONS = (('StrictHostKeyChecking', 'no'),
                       ('UpdateHostKeys', 'no'),
                       ('ControlPath', '~/.ssh/avocado-master-%r@%h:%p'))

    MASTER_OPTIONS = (('ControlMaster', 'yes'),
                      ('ControlPersist', 'yes'))

    def __init__(self, host, port=None, user=None, key=None):
        """
        :param host: a host name or IP address
        :type host: str
        :param port: port number
        :type port: int
        :param user: the name of the remote user
        :type user: str
        :param key: path to a key for authentication purpose
        :type key: str
        """
        self.host = host
        self.port = port
        self.user = user
        self.key = key
        self._connection = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        return self.quit()

    def _dash_o_opts_to_str(self, opts):
        """
        Transforms tuples into options that should be given by "-o Key=Val"
        """
        return " ".join(["-o '%s=%s'" % (_[0], _[1]) for _ in opts])

    def _ssh_cmd(self, dash_o_opts=(), opts=(), command=''):
        cmd = self._dash_o_opts_to_str(dash_o_opts)
        if self.user is not None:
            cmd += " -l %s" % self.user
            if self.key is not None:
                cmd += " -i %s" % self.key
        if self.port is not None:
            cmd += " -p %s" % self.port
        cmd = "ssh %s %s %s '%s'" % (cmd, " ".join(opts), self.host, command)
        return cmd

    def _master_connection(self):
        return self._ssh_cmd(self.DEFAULT_OPTIONS + self.MASTER_OPTIONS, ('-n',))

    def _master_command(self, command):
        cmd = self._ssh_cmd(self.DEFAULT_OPTIONS, ('-O', command))
        result = process.run(cmd, ignore_status=True)
        return result.exit_status == 0

    def _check(self):
        return self._master_command('check')

    def connect(self):
        """
        Establishes the connection to the remote endpoint

        On this implementation, it means creating the master connection,
        which is a process that will live while and be used for subsequent
        commands.

        :returns: whether the connection is successfully established
        :rtype: bool
        """
        if not self._check():
            master = process.run(self._master_connection(), ignore_status=True)
            if not master.exit_status == 0:
                return False
            self._connection = master
        return self._check()

    def cmd(self, command):
        """
        Runs a command over the SSH session

        Errors, such as an exit status different than 0, should be checked by
        the caller.

        :param command: the command to execute over the SSH session
        :param command: str
        :returns: The command result object.
        :rtype: A :class:`CmdResult` instance.
        """
        cmd = self._ssh_cmd(self.DEFAULT_OPTIONS, ('-q', ), command)
        return process.run(cmd, ignore_status=True)

    def quit(self):
        """
        Attempts to gracefully end the session, by finishing the master process

        :returns: if closing the session was successful or not
        :rtype: bool
        """
        return self._master_command('exit')
