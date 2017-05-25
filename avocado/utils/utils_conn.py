"""
connection tools to manage kinds of connection.
"""

import logging
import os
import shutil
import tempfile

import aexpect
from . import path

import propcan
import remote
import data_dir


class ConnectionError(Exception):

    """
    The base error in connection.
    """
    pass


class ConnForbiddenError(ConnectionError):

    """
    Error in forbidden operation.
    """

    def __init__(self, detail):
        ConnectionError.__init__(self)
        self.detail = detail

    def __str__(self):
        return ('Operation is forbidden.\n'
                'Message: %s' % self.detail)


class ConnNotImplementedError(ConnectionError):

    """
    Error in calling unimplemented method
    """

    def __init__(self, method_type, class_type):
        ConnectionError.__init__(self)
        self.method_type = method_type
        self.class_type = class_type

    def __str__(self):
        return ('Method %s is not implemented in class %s\n'
                % (self.method_type, self.class_type))


class ConnLoginError(ConnectionError):

    """
    Error in login.
    """

    def __init__(self, dest, detail):
        ConnectionError.__init__(self)
        self.dest = dest
        self.detail = detail

    def __str__(self):
        return ("Got a error when login to %s.\n"
                "Error: %s\n" % (self.dest, self.detail))


class ConnToolNotFoundError(ConnectionError):

    """
    Error in not found tools.
    """

    def __init__(self, tool, detail):
        ConnectionError.__init__(self)
        self.tool = tool
        self.detail = detail

    def __str__(self):
        return ("Got a error when access the tool (%s).\n"
                "Error: %s\n" % (self.tool, self.detail))


class SSHCheckError(ConnectionError):

    """
    Base Error in check of SSH connection.
    """

    def __init__(self, server_ip, output):
        ConnectionError.__init__(self)
        self.server_ip = server_ip
        self.output = output

    def __str__(self):
        return ("SSH to %s failed.\n"
                "output: %s " % (self.server_ip, self.output))


class SSHRmAuthKeysError(ConnectionError):

    """
    Error in removing authorized_keys file.
    """

    def __init__(self, auth_keys, output):
        ConnectionError.__init__(self)
        self.auth_keys = auth_keys
        self.output = output

    def __str__(self):
        return ("Failed to remove authorized_keys file (%s).\n"
                "output: %s .\n" % (self.auth_keys, self.output))


class ConnCmdClientError(ConnectionError):

    """
    Error in executing cmd on client.
    """

    def __init__(self, cmd, output):
        ConnectionError.__init__(self)
        self.cmd = cmd
        self.output = output

    def __str__(self):
        return ("Execute command '%s' on client failed.\n"
                "output: %s" % (self.cmd, self.output))


class ConnServerRestartError(ConnectionError):

    """
    Error in restarting libvirtd on server.
    """

    def __init__(self, output):
        ConnectionError.__init__(self)
        self.output = output

    def __str__(self):
        return ("Failed to restart libvirtd service on server.\n"
                "output: %s.\n" % (self.output))


class ConnectionBase(propcan.PropCanBase):

    """
    Base class of a connection between server and client.

    Connection is build to from client to server. And there are
    some information for server and client in ConnectionBase.
    """
    __slots__ = ('server_ip', 'server_user', 'server_pwd',
                 'client_ip', 'client_user', 'client_pwd',
                 'server_session', 'client_session',
                 'tmp_dir', 'auto_recover')

    def __init__(self, *args, **dargs):
        """
        Initialize instance with server info and client info.

        :param server_ip: Ip of server.
        :param server_user: Username to login server.
        :param server_pwd: Password for server_user.
        :param client_ip: IP of client.
        :param client_user: Username to login client.
        :param client_pwd: Password for client_user.
        :param server_session: Session to server and execute command on
                               server.
        :param client_session: Session to client and execute command on
                               client.
        :param tmp_dir: A tmp dir to store some tmp file.
        :param auto_recover: If it is False same as the default,
                             conn_recover() will not called by __del__()
                             If it is True, Connection class will call
                             conn_recover() in __del__(), then user need not
                             call it manually. But the errors in conn_recover()
                             will be ignored.

        Example:

        ::

          connection = ConnectionBase(server_ip=server_ip,
                                      server_user=server_user,
                                      server_pwd=server_pwd,
                                      client_ip=client_ip,
                                      client_user=client_user,
                                      client_pwd=client_pwd)
          connection.conn_setup()
          virsh.connect(URI)
          connection.conn_recover()

        We suggest *not* to pass auto_recover=True to __init__(),
        and call conn_recover() manually when you don't need this
        connection any more.
        """
        init_dict = dict(*args, **dargs)
        init_dict['server_ip'] = init_dict.get('server_ip', 'SERVER.IP')
        init_dict['server_user'] = init_dict.get('server_user', 'root')
        init_dict['server_pwd'] = init_dict.get('server_pwd', None)
        init_dict['client_ip'] = init_dict.get('client_ip', 'CLIENT.IP')
        init_dict['client_user'] = init_dict.get('client_user', 'root')
        init_dict['client_pwd'] = init_dict.get('client_pwd', None)
        init_dict['auto_recover'] = init_dict.get('auto_recover', False)
        super(ConnectionBase, self).__init__(init_dict)

        self.__dict_set__('client_session', None)
        self.__dict_set__('server_session', None)

        # make a tmp dir as a workspace
        tmp_dir = tempfile.mkdtemp(dir=data_dir.get_tmp_dir())
        if not os.path.isdir(tmp_dir):
            os.makedirs(tmp_dir)
        self.tmp_dir = tmp_dir

    def __del__(self):
        """
        Clean up any leftover sessions and tmp_dir.
        """
        self.close_session()
        if self.auto_recover:
            try:
                self.conn_recover()
            except ConnNotImplementedError:
                pass
        tmp_dir = self.tmp_dir
        if (tmp_dir is not None) and (os.path.exists(tmp_dir)):
            shutil.rmtree(tmp_dir)

    def close_session(self):
        """
        If some session exists, close it down.
        """
        session_list = ['client_session', 'server_session']
        for session_name in session_list:
            session = self.__dict_get__(session_name)
            if session is not None:
                session.close()
            else:
                continue

    def conn_setup(self):
        """
        waiting for implemented by subclass.
        """
        raise ConnNotImplementedError('conn_setup', self.__class__)

    def conn_check(self):
        """
        waiting for implemented by subclass.
        """
        raise ConnNotImplementedError('conn_check', self.__class__)

    def conn_recover(self):
        """
        waiting for implemented by subclass.
        """
        raise ConnNotImplementedError('conn_recover', self.__class__)

    def _new_client_session(self):
        """
        Build a new client session.
        """
        transport = 'ssh'
        host = self.client_ip
        port = 22
        username = self.client_user
        password = self.client_pwd
        prompt = r"[\#\$]\s*$"
        try:
            client_session = remote.wait_for_login(transport, host, port,
                                                   username, password, prompt)
        except remote.LoginTimeoutError:
            raise ConnLoginError(host, "Got a timeout error when login.")
        except remote.LoginAuthenticationError:
            raise ConnLoginError(host, "Authentication failed to login.")
        except remote.LoginProcessTerminatedError:
            raise ConnLoginError(host, "Host terminates during login.")
        except remote.LoginError:
            raise ConnLoginError(host, "Some error occurs login failed.")

        return client_session

    def get_client_session(self):
        """
        If the client session exists,return it.
        else create a session to client and set client_session.
        """
        client_session = self.__dict_get__('client_session')

        if (client_session is not None) and (client_session.is_alive()):
            return client_session
        else:
            client_session = self._new_client_session()

        self.__dict_set__('client_session', client_session)
        return client_session

    @classmethod
    def set_client_session(cls, value):
        """
        Set client session to value.
        """
        if value:
            message = "Forbid to set client_session to %s." % value
        else:
            message = "Forbid to set client_session."

        raise ConnForbiddenError(message)

    @classmethod
    def del_client_session(cls):
        """
        Delete client session.
        """
        raise ConnForbiddenError('Forbid to del client_session')

    def _new_server_session(self):
        """
        Build a new server session.
        """
        transport = 'ssh'
        host = self.server_ip
        port = 22
        username = self.server_user
        password = self.server_pwd
        prompt = r"[\#\$]\s*$"
        try:
            server_session = remote.wait_for_login(transport, host, port,
                                                   username, password, prompt)
        except remote.LoginTimeoutError:
            raise ConnLoginError(host, "Got a timeout error when login.")
        except remote.LoginAuthenticationError:
            raise ConnLoginError(host, "Authentication failed to login.")
        except remote.LoginProcessTerminatedError:
            raise ConnLoginError(host, "Host terminates during login.")
        except remote.LoginError:
            raise ConnLoginError(host, "Some error occurs login.")

        return server_session

    def get_server_session(self):
        """
        If the server session exists,return it.
        else create a session to server and set server_session.
        """
        server_session = self.__dict_get__('server_session')

        if (server_session is not None) and (server_session.is_alive()):
            return server_session
        else:
            server_session = self._new_server_session()

        self.__dict_set__('server_session', server_session)
        return server_session

    @classmethod
    def set_server_session(cls, value=None):
        """
        Set server session to value.
        """
        if value:
            message = "Forbid to set server_session to %s." % value
        else:
            message = "Forbid to set server_session."

        raise ConnForbiddenError(message)

    @classmethod
    def del_server_session(cls):
        """
        Delete server session.
        """
        raise ConnForbiddenError('Forbid to del server_session')


class SSHConnection(ConnectionBase):

    """
    Connection of SSH transport.

    Some specific variables in SSHConnection class.

    ssh_rsa_pub_path: Path of id_rsa.pub, default is /root/.ssh/id_rsa.pub.
    ssh_id_rsa_path: Path of id_rsa, default is /root/.ssh/id_rsa.
    SSH_KEYGEN, SSH_ADD, SSH_COPY_ID, SSH_AGENT, SHELL, SSH: tools to build
    a non-pwd connection.
    """
    __slots__ = ('ssh_rsa_pub_path', 'ssh_id_rsa_path', 'SSH_KEYGEN',
                 'SSH_ADD', 'SSH_COPY_ID', 'SSH_AGENT', 'SHELL', 'SSH')

    def __init__(self, *args, **dargs):
        """
        Initialization of SSH connection.

        (1). Call __init__ of class ConnectionBase.
        (2). Initialize tools will be used in conn setup.
        """
        init_dict = dict(*args, **dargs)
        print init_dict
        init_dict['ssh_rsa_pub_path'] = init_dict.get('ssh_rsa_pub_path',
                                                      '/root/.ssh/id_rsa.pub')
        init_dict['ssh_id_rsa_path'] = init_dict.get('ssh_id_rsa_path',
                                                     '/root/.ssh/id_rsa')
        super(SSHConnection, self).__init__(init_dict)
        # set the tool for ssh setup.
        tool_dict = {'SSH_KEYGEN': 'ssh-keygen',
                     'SSH_ADD': 'ssh-add',
                     'SSH_COPY_ID': 'ssh-copy-id',
                     'SSH_AGENT': 'ssh-agent',
                     'SHELL': 'sh',
                     'SSH': 'ssh'}

        for key in tool_dict:
            tool_name = tool_dict[key]
            try:
                tool = path.find_command(tool_name)
            except path.CmdNotFoundError:
                logging.debug("%s executable not set or found on path,"
                              "some function of connection will fail.",
                              tool_name)
                tool = '/bin/true'
            self.__dict_set__(key, tool)

    def conn_check(self):
        """
        Check the SSH connection.

        (1).Initialize some variables.
        (2).execute ssh command to check conn.
        """
        client_session = self.client_session
        server_user = self.server_user
        server_ip = self.server_ip
        ssh = self.SSH
        if ssh is '/bin/true':
            raise ConnToolNotFoundError('ssh',
                                        "exec not set or found on path, ")

        cmd = "%s %s@%s exit 0" % (ssh, server_user, server_ip)
        try:
            client_session.cmd(cmd, timeout=5)
        except aexpect.ShellError, detail:
            client_session.close()
            raise SSHCheckError(server_ip, detail)
        logging.debug("Check the SSH to %s OK.", server_ip)

    def conn_recover(self):
        """
        Clean up authentication host.
        """
        # initialize variables
        server_ip = self.server_ip
        server_user = self.server_user
        server_pwd = self.server_pwd

        ssh_authorized_keys_path = '/root/.ssh/authorized_keys'
        cmd = "rm -rf %s" % ssh_authorized_keys_path

        print server_ip
        server_session = remote.wait_for_login('ssh', server_ip, '22',
                                               server_user, server_pwd,
                                               r"[\#\$]\s*$")
        # remove authentication file
        status, output = server_session.cmd_status_output(cmd)
        if status:
            raise SSHRmAuthKeysError(ssh_authorized_keys_path, output)

        # restart libvirtd service on server
        try:
            server_session.close()
        except (remote.LoginError, aexpect.ShellError), detail:
            server_session.close()
            raise ConnServerRestartError(detail)

        logging.debug("SSH authentication recover successfully.")

    def conn_setup(self, timeout=10):
        """
        Setup of SSH connection.

        (1).Initialization of some variables.
        (2).Check tools.
        (3).Initialization of id_rsa.
        (4).set a ssh_agent.
        (5).copy pub key to server.

        :param timeout: The time duration (in seconds) to wait for prompts
        """
        client_session = self.client_session
        ssh_rsa_pub_path = self.ssh_rsa_pub_path
        ssh_id_rsa_path = self.ssh_id_rsa_path
        server_user = self.server_user
        server_ip = self.server_ip
        server_pwd = self.server_pwd
        ssh_keygen = self.SSH_KEYGEN
        ssh_add = self.SSH_ADD
        ssh_copy_id = self.SSH_COPY_ID
        ssh_agent = self.SSH_AGENT
        shell = self.SHELL
        assert timeout >= 0, 'Invalid timeout value: %s' % timeout

        tool_dict = {'ssh_keygen': ssh_keygen,
                     'ssh_add': ssh_add,
                     'ssh_copy_id': ssh_copy_id,
                     'ssh_agent': ssh_agent,
                     'shell': shell}
        for tool_name in tool_dict:
            tool = tool_dict[tool_name]
            if tool is '/bin/true':
                raise ConnToolNotFoundError(tool_name,
                                            "exec not set or found on path,")

        if os.path.exists("/root/.ssh/id_rsa"):
            pass
        else:
            cmd = "%s -t rsa -f /root/.ssh/id_rsa -N '' " % (ssh_keygen)
            status, output = client_session.cmd_status_output(cmd)
            if status:
                raise ConnCmdClientError(cmd, output)

        cmd = "%s %s" % (ssh_agent, shell)
        status, output = client_session.cmd_status_output(cmd)
        if status:
            raise ConnCmdClientError(cmd, output)

        cmd = "%s %s" % (ssh_add, ssh_id_rsa_path)
        status, output = client_session.cmd_status_output(cmd)
        if status:
            raise ConnCmdClientError(cmd, output)

        cmd = "%s -i %s %s@%s" % (ssh_copy_id, ssh_rsa_pub_path,
                                  server_user, server_ip)
        client_session.sendline(cmd)
        try:
            remote.handle_prompts(client_session, server_user,
                                  server_pwd, prompt=r"[\#\$]\s*$",
                                  timeout=timeout)
        except remote.LoginError, detail:
            raise ConnCmdClientError(cmd, detail)

        client_session.close()
        logging.debug("SSH connection setup successfully.")
