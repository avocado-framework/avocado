#!/usr/bin/env python

'''
Created on Dec 6, 2013

:author: jzupka
'''
import sys
import time
import inspect
import remote_interface
import messenger


def getsource(obj):
    return inspect.getsource(obj)


def wait_timeout(timeout):
    if timeout is None:
        while 1:
            yield True
    else:
        end_time = time.time() + timeout
        while time.time() < end_time:
            yield True


class CmdMaster(object):

    """
    Representation of BaseCmd on master side.
    """

    def __init__(self, commander, name, *args, **kargs):
        """
        :params commander: Commander from which was command started.
        :params name: Name parsed to string representation
        :type name: [str, str, str]
        :parmas args: list to arguments to cmd.
        :type args: []
        :params kargs: {}
        """
        self._basecmd = remote_interface.BaseCmd(name, *args, **kargs)
        self.commander = commander
        self._stdout = ""
        self._stderr = ""
        self._results_cnt = 0
        self._stdout_cnt = 0
        self._stderr_cnt = 0

    def getbasecmd(self):
        """
        Property basecmd getter
        """
        self._results_cnt = 0
        return self._basecmd

    def setbasecmd(self, value):
        """
        Property basecmd setter _resuls_cnt identify if value was change from
        last reading.
        """

        self._basecmd = value
        self._results_cnt += 1

    basecmd = property(getbasecmd, setbasecmd)

    def getstdout(self):
        """
        Property stdout getter
        """
        self._stdout_cnt = 0
        return self._stdout

    def setstdout(self, value):
        """
        Property stdout setter _stdout_cnt identify if value was change from
        last reading.
        """
        self._stdout = value
        self._stdout_cnt += 1

    stdout = property(getstdout, setstdout)

    def getstderr(self):
        """
        Property stderr getter
        """
        self._stderr_cnt = 0
        return self._stderr

    def setstderr(self, value):
        """
        Property stderr setter _stderr_cnt identify if value was change from
        last reading.
        """
        self._stderr = value
        self._stderr_cnt += 1

    stderr = property(getstderr, setstderr)

    def send_stdin(self, msg):
        """
        Send data to stdin
        """
        self.commander.manage.send_msg(msg, self.basecmd.cmd_id)

    def wait(self):
        """
        Wait until command return results.
        """
        return self.commander.wait(self)

    def wait_response(self, timeout=None):
        """
        Wait until command return any cmd.
        """
        self.commander.wait_response(self, timeout)

    def __getattr__(self, name):
        """
        Shortcut to encapsulated basecmd.
        """
        if name in ["__getstate__", "__setstate__", "__slots__"]:
            raise AttributeError()
        return getattr(self.basecmd, name)

    def set_commander(self, commander):
        """
        For nohup commands it allows connect cmd to new created commander.
        """
        self.commander = commander
        if self not in commander.cmds:
            commander.cmds[self.cmd_id] = self
        self.commander.manage.register_cmd(self.basecmd,
                                           remote_interface.BaseCmd.single_cmd_id)


class CmdEncapsulation(object):

    """
    Class parse command name   cmd.nohup.shell -> ["nohup", "shell"]
    """

    def __init__(self, master, obj_name, name):
        self.master = master
        if obj_name is None:
            self.name = [name]
        else:
            self.name = obj_name + [name]
        self.cmd = None

    def __getattr__(self, name):
        return CmdEncapsulation(self.master, self.name, name)

    def __call__(self, *args, **kargs):
        """
        Call commander with specific command.
        """
        self.cmd = CmdMaster(self.master, self.name, *args, **kargs)
        return self.master.cmd(self.cmd)


class CmdTimeout(remote_interface.MessengerError):

    """
    Raised when waiting for cmd exceeds time define by timeout.
    """

    def __init__(self, msg):
        super(CmdTimeout, self).__init__(msg)

    def __str__(self):
        return "Commander Timeout %s" % (self.msg)


class Commander(object):

    """
    Commander representation for transfer over network.
    """
    __slots__ = []


class CommanderMaster(messenger.Messenger):

    """
    Class commander master is responsible for communication with commander
    slave. It invoke commands to slave part and receive messages from them.
    For communication is used only stdin and stdout which are streams from
    slave part.
    """

    def __init__(self, stdin, stdout, debug=False):
        """
        :type stdin: IOWrapper with implemented write function.
        :type stout: IOWrapper with implemented read function.
        """
        super(CommanderMaster, self).__init__(stdin, stdout)
        self.cmds = {}
        self.debug = debug

        self.flush_stdin()
        self.write_msg("start")
        succ, msg = self.read_msg()
        if not succ or msg != "Started":
            raise remote_interface.CommanderError("Remote commander"
                                                  " not started.")

    def close(self):
        try:
            self.manage.exit()
        except Exception:
            pass
        super(CommanderMaster, self).close()

    def __getattr__(self, name):
        """
        Start parsing unknown attribute in cmd.
        """
        if name in ["__getstate__", "__setstate__", "__slots__"]:
            raise AttributeError()
        return CmdEncapsulation(self, None, name)

    def __deepcopy__(self, memo):
        """
        Replace deepcopy by substituting by network Commander version.
        """
        result = Commander.__new__(Commander)
        memo[id(self)] = result
        return result

    def listen_streams(self, cmd):
        """
        Listen on all streams included in Commander commands.
        """
        if isinstance(cmd, remote_interface.StdStream):
            if (self.debug):
                print cmd.msg
            if cmd.isCmdMsg():
                if isinstance(cmd, remote_interface.StdOut):
                    self.cmds[cmd.cmd_id].stdout += cmd.msg
                elif isinstance(cmd, remote_interface.StdErr):
                    self.cmds[cmd.cmd_id].stderr += cmd.msg
            else:
                if isinstance(cmd, remote_interface.StdOut):
                    sys.stdout.write(cmd.msg)
                elif isinstance(cmd, remote_interface.StdErr):
                    sys.stderr.write(cmd.msg)

    def listen_errors(self, cmd):
        """
        Listen for errors raised from slave part of commander.
        """
        if isinstance(cmd, (Exception, remote_interface.CommanderError,
                            remote_interface.MessengerError)):
            raise cmd

    def listen_cmds(self, cmd):
        """
        Manage basecmds from slave side.
        """
        if isinstance(cmd, remote_interface.BaseCmd):
            if (self.debug):
                print cmd.func, cmd.results, cmd._finished

            if isinstance(cmd.results, Exception):
                raise cmd.results
            if cmd.cmd_id in self.cmds:
                self.cmds[cmd.cmd_id].basecmd.update(cmd)
                self.cmds[cmd.cmd_id].basecmd.update_cmd_hash(cmd)

    def listen_messenger(self, timeout=60):
        """
        Wait for msg from slave side and take care about them.
        """
        succ, r_cmd = self.read_msg(timeout)
        if succ is None:
            return r_cmd
        if not succ:
            raise remote_interface.CommanderError("Remote process died.")

        self.listen_errors(r_cmd)
        self.listen_streams(r_cmd)
        self.listen_cmds(r_cmd)
        return r_cmd

    def cmd(self, cmd, timeout=60):
        """
        Invoke command on client side.
        """
        self.cmds[cmd.basecmd.cmd_id] = cmd
        self.write_msg(cmd.basecmd)
        while (1):
            if cmd.basecmd.func[0] not in ["async", "nohup"]:
                # If not async wait for finish.
                self.wait(cmd, timeout)
            else:
                ancmd = self.wait_response(cmd, timeout)
                cmd.update_cmd_hash(ancmd)
            return cmd

    def wait(self, cmd, timeout=60):
        """
        Wait until command return results.
        """
        if cmd.cmd_id not in self.cmds:
            return cmd
        m_cmd = self.cmds[cmd.cmd_id]
        if m_cmd.is_finished():
            return m_cmd

        r_cmd = None

        time_step = None
        if timeout is not None:
            time_step = timeout / 10.0
        w = wait_timeout(timeout)
        for _ in w:
            r_cmd = self.listen_messenger(time_step)
            if isinstance(r_cmd, remote_interface.BaseCmd):
                if (self.debug):
                    print m_cmd._stdout
                if r_cmd is not None and r_cmd == m_cmd.basecmd:
                    # If command which we waiting for.
                    if r_cmd.is_finished():
                        del self.cmds[m_cmd.basecmd.cmd_id]
                        m_cmd.basecmd.update(r_cmd)
                        return m_cmd
                    m_cmd.basecmd.update(r_cmd)
                    m_cmd.basecmd.update_cmd_hash(r_cmd)

        if r_cmd is None:
            raise CmdTimeout("%ss during %s" % (timeout, str(cmd)))

    def wait_response(self, cmd, timeout=60):
        """
        Wait until command return any cmd.
        """
        if cmd.cmd_id not in self.cmds:
            return cmd
        if cmd.is_finished() or cmd._stdout_cnt or cmd._stderr_cnt:
            return cmd
        m_cmd = self.cmds[cmd.cmd_id]

        r_cmd = None

        time_step = None
        if timeout is not None:
            time_step = timeout / 10.0
        w = wait_timeout(timeout)
        while (w.next()):
            r_cmd = self.listen_messenger(time_step)
            if r_cmd is not None and r_cmd == m_cmd.basecmd:
                return m_cmd

        if r_cmd is None:
            raise CmdTimeout(timeout)
