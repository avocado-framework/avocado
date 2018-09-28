from . import process


class Session(object):
    """
    Represents an SSH session to a remote system, for the purpose of
    executing commands remotely.
    """

    DEFAULT_OPTIONS = (('StrictHostKeyChecking', 'no'),
                       ('UpdateHostKeys', 'no'))

    MASTER_OPTIONS = (('ControlMaster', 'yes'),
                      ('ControlPersist', 'yes'))

    def __init__(self, address, credentials):
        """
        :param address: a hostname or IP address and port, in the same format
                        given to socket and other servers
        :type address: tuple
        :param credentials: username and path to a key for authentication purposes
        :type credentials: tuple
        """
        self.address = address
        self.credentials = credentials
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
        if self.credentials:
            cmd += " -l %s" % self.credentials[0]
            if self.credentials[1] is not None:
                cmd += " -i %s" % self.credentials[1]
        if self.address[1] is not None:
            cmd += " -p %s" % self.address[1]
        cmd = "ssh %s %s %s '%s'" % (cmd, " ".join(opts), self.address[0], command)
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
        return True

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
