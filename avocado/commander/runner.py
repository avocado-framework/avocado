#!/usr/bin/env python

'''
Created on Dec 6, 2013

:author: jzupka
'''

import os
import sys
import select
import time
import stat
import gc
import logging
import traceback
import subprocess
import string
import random
import shutil
import signal

import remote_interface
import messenger as ms


def daemonize(pipe_root_path="/tmp"):
    """
    Init daemon.

    :param pipe_root_path: path to directory for pipe.
    :return: [True if child, stdin_path, stdou_path, stderr_path]
    """
    def is_file_open(path):
        """
        Determine process which open file.

        :param path: Path to file.
        :return: [[pid,mode], ... ].
        """
        opens = []
        pids = os.listdir('/proc')
        for pid in sorted(pids):
            try:
                int(pid)
            except ValueError:
                continue
            fd_dir = os.path.join('/proc', pid, 'fd')
            try:
                for filepath in os.listdir(fd_dir):
                    try:
                        p = os.path.join(fd_dir, filepath)
                        link = os.readlink(os.path.join(fd_dir, filepath))
                        if link == path:
                            mode = os.lstat(p).st_mode
                            opens.append([pid, mode])
                    except OSError:
                        continue
            except OSError, e:
                if e.errno == 2:
                    continue
                raise
        return opens

    def daemonize():
        """
        Run guest as a daemon.
        """
        gc_was_enabled = gc.isenabled()
        # Disable gc to avoid bug where gc -> file_dealloc ->
        # write to stderr -> hang.  http://bugs.python.org/issue1336
        gc.disable()
        try:
            pid = os.fork()
            if gc_was_enabled:
                gc.enable()
            if pid > 0:  # If parent return False
                os.waitpid(pid, 0)
                return 0
        except OSError, e:
            sys.stderr.write("Daemonize failed: %s\n" % (e))
            sys.exit(1)

        os.chdir("/")
        os.setsid()
        os.umask(0)

        try:
            pid = os.fork()
            if gc_was_enabled:
                gc.enable()
            if pid > 0:  # If parent Exit
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("Daemonize failed: %s\n" % (e))
            sys.exit(1)

        if gc_was_enabled:
            gc.enable()

        sys.stdout.flush()
        sys.stderr.flush()
        return 1

    stdin_path = os.path.join(pipe_root_path, "stdin")
    stdout_path = os.path.join(pipe_root_path, "stdout")
    stderr_path = os.path.join(pipe_root_path, "stderr")
    results_path = os.path.join(pipe_root_path, "results")
    inputs_path = os.path.join(pipe_root_path, "inputs")

    for f in [stdin_path, stdout_path, stderr_path, results_path, inputs_path]:
        try:
            os.mkfifo(f)
        except OSError, e:
            if e.errno == 17:
                pass

    # Check for a pidfile to see if the daemon already runs
    openers = is_file_open(stdout_path)
    rundaemon = False
    if len(openers) > 0:
        for i in openers:
            if i[1] & stat.S_IWUSR:
                rundaemon = True
                openers.remove(i)
        if len(openers) > 0:
            for i in openers:
                os.kill(int(i[0]), 9)
    time.sleep(0.3)

    # Start the daemon
    child = False
    if not rundaemon:
        child = daemonize()

    if child == 0:
        return (child,
                inputs_path,
                results_path,
                stdin_path,
                stdout_path,
                stderr_path)
    else:
        signal.signal(signal.SIGIO, signal.SIG_DFL)
        return (child,
                results_path,
                inputs_path,
                stdin_path,
                stdout_path,
                stderr_path)


def create_process_cmd():
    """
    Create child process without clean process data thanks that it is possible
    call function and classes from child process.
    """
    r_c, w_p = os.pipe()
    r_p, w_c = os.pipe()
    r_si, w_si = os.pipe()
    r_so, w_so = os.pipe()
    r_se, w_se = os.pipe()
    gc_was_enabled = gc.isenabled()
    # Disable gc to avoid bug where gc -> file_dealloc ->
    # write to stderr -> hang.  http://bugs.python.org/issue1336
    gc.disable()
    pid = os.fork()
    if pid == 0:  # Child process
        os.close(r_p)
        os.close(w_p)
        os.close(w_si)
        os.close(r_so)
        os.close(r_se)
        sys.stdin.close()
        sys.stdout.close()
        sys.stderr.close()
        sys.stdin = os.fdopen(r_si, 'r', 0)
        sys.stdout = os.fdopen(w_so, 'w', 0)
        sys.stderr = os.fdopen(w_se, 'w', 0)
        if gc_was_enabled:
            gc.enable()
        return (0, r_c, w_c, None, None, None)
    else:
        os.close(r_c)
        os.close(w_c)
        os.close(r_si)
        os.close(w_so)
        os.close(w_se)
        if gc_was_enabled:
            gc.enable()
        return (pid, r_p, w_p, w_si, r_so, r_se)


def gen_tmp_dir(root_path):
    """
    Try to create tmp dir with special name.
    """
    path = None
    while (path is None or os.path.exists(path)):
        rname = "runner" + "".join(random.sample(string.letters, 4))
        path = os.path.join(root_path, rname)
        try:
            if not os.path.exists(path):
                os.mkdir(path)
                return path
        except:
            continue


def clean_tmp_dir(path):
    """
    Clean up directory.
    """
    shutil.rmtree(path, True)


def sort_fds_event(fds):
    hup = [x[0] for x in fds if x[1] & select.POLLHUP]
    read = [x[0] for x in fds if x[1] & select.POLLIN]
    write = [x[0] for x in fds if x[1] & select.POLLOUT]
    return hup, read, write


def close_unused_fds(fds):
    """
    Close all file descriptors which are not necessary anymore.

    :param fds: file descriptors
    :type fds: list []
    """
    for fd in fds:
        os.close(fd)


class CmdFinish(object):

    """
    Class used for communication with child process. This class
    """
    __slots__ = ["pid"]

    def __init__(self, parent=False):
        if not parent:
            self.pid = os.getpid()
        else:
            self.pid = os.getppid()
        self.pid = self.pid


class CmdSlave(object):

    """
    Representation of BaseCmd on slave side.
    """

    def __init__(self, baseCmd):
        """
        :param baseCmd: basecmd for encapsulation.
        """
        self.basecmd = baseCmd
        self.cmd_id = baseCmd.cmd_id
        self.obj = None
        self.pid = None
        self.r_pipe = None
        self.w_pipe = None
        self.stdin_pipe = None
        self.stdout_pipe = None
        self.stderr_pipe = None
        self.async = False
        self.nohup = False
        self.manage = False
        self.msg = None

    def close_pipes(self):
        """
        Close command communication pipe.
        """
        if self.r_pipe is not None:
            os.close(self.r_pipe)
        if self.w_pipe is not None:
            os.close(self.w_pipe)
        if self.stdin_pipe is not None:
            os.close(self.stdin_pipe)
        if self.stdout_pipe is not None:
            os.close(self.stdout_pipe)
        if self.stderr_pipe is not None:
            os.close(self.stderr_pipe)

    def parse_func_name(self, func_name, commander):
        """
        Parse name sended from master.

        format: ``["manage|async|nohup| ", "fnname1", "fnname2", ...]``

        :param func_name: Function name
        :param commander: Where to execute the command (remote or local)
        """
        if func_name[0] == "manage":  # start command in main process.
            self.manage = True
            func_name = func_name[1:]
        if func_name[0] == "async":  # start command in new process.
            self.async = True
            func_name = func_name[1:]
        if func_name[0] == "nohup":  # start command in new daemon process.
            self.nohup = True
            func_name = func_name[1:]
        if hasattr(commander, func_name[0]):
            obj = getattr(commander, func_name[0])
        elif func_name[0] in commander.globals:
            obj = commander.globals[func_name[0]]
        elif func_name[0] in commander.locals:
            obj = commander.locals[func_name[0]]
        else:
            obj = globals()[func_name[0]]
        if len(func_name) > 1:
            for name in func_name[1:]:
                obj = getattr(obj, name)
        return obj

    def __call__(self, commander):
        """
        Call command cmd(*args, **kargs)
        """
        self.obj = self.parse_func_name(self.basecmd.func, commander)
        if self.manage:  # start command in main process
            self.basecmd.results = self.obj(*self.basecmd.args,
                                            **self.basecmd.kargs)
            self.basecmd._finished = True
            self.finish(commander)
        elif self.async:  # start command in new process
            self.basecmd.results = self.__call_async__(commander)
            self.basecmd._async = True
        elif self.nohup:   # start command in new daemon process
            if self.basecmd.cmd_hash is None:
                self.basecmd.cmd_hash = gen_tmp_dir("/tmp")
            self.basecmd.results = self.__call_nohup__(commander)
            self.basecmd._async = True
        else:  # start command in new process but wait for input.
            self.basecmd.results = self.__call_async__(commander)

    def __call_async__(self, commander):
        (self.pid, self.r_pipe, self.w_pipe, self.stdin_pipe,
         self.stdout_pipe, self.stderr_pipe) = create_process_cmd()
        if self.pid == 0:  # Child process make commands
            commander._close_cmds_stdios(self)
            self.msg = ms.Messenger(ms.StdIOWrapperIn(self.r_pipe),
                                    ms.StdIOWrapperOut(self.w_pipe))
            try:
                self.basecmd.results = self.obj(*self.basecmd.args,
                                                **self.basecmd.kargs)
            except Exception:
                err_msg = traceback.format_exc()
                self.msg.write_msg(remote_interface.CmdTraceBack(err_msg))
                sys.exit(-1)
            finally:
                self.msg.write_msg(self.basecmd.results)
                self.msg.write_msg(CmdFinish())
            sys.exit(0)
        else:  # Parent process create communication interface to child process
            self.msg = ms.Messenger(ms.StdIOWrapperIn(self.r_pipe),
                                    ms.StdIOWrapperOut(self.w_pipe))

    def __call_nohup__(self, commander):
        (pid, self.r_path, self.w_path, self.stdin_path, self.stdout_path,
         self.stderr_path) = daemonize(self.basecmd.cmd_hash)
        if pid == 1:  # Child process make commands
            commander._close_cmds_stdios(self)
            (self.pid, r_pipe, w_pipe, stdin_pipe,
             stdout_pipe, stderr_pipe) = create_process_cmd()
            if self.pid == 0:  # Child process make commands
                self.msg = ms.Messenger(ms.StdIOWrapperIn(r_pipe),
                                        ms.StdIOWrapperOut(w_pipe))
                try:
                    self.basecmd.results = self.obj(*self.basecmd.args,
                                                    **self.basecmd.kargs)
                except Exception:
                    err_msg = traceback.format_exc()
                    self.msg.write_msg(remote_interface.CmdTraceBack(err_msg))
                    sys.exit(-1)
                finally:
                    self.msg.write_msg(self.basecmd.results)
                sys.exit(0)
            else:
                # helper child process open communication pipes.
                # This process is able to manage problem with connection width
                # main parent process. It allows start unchanged child process.
                self.r_pipe = os.open(self.r_path, os.O_RDONLY)
                self.w_pipe = os.open(self.w_path, os.O_WRONLY)
                sys.stdout = os.fdopen(os.open(self.stdout_path, os.O_WRONLY),
                                       "w",
                                       0)
                sys.stderr = os.fdopen(os.open(self.stderr_path, os.O_WRONLY),
                                       "w",
                                       0)
                sys.stdin = os.fdopen(os.open(self.stdin_path, os.O_RDONLY),
                                      "r",
                                      0)

                w_fds = [r_pipe, w_pipe, stdin_pipe, stdout_pipe, stderr_pipe]
                m_fds = [self.r_pipe,
                         self.w_pipe,
                         sys.stdin.fileno(),
                         sys.stdout.fileno(),
                         sys.stderr.fileno()]
                p = select.poll()
                p.register(r_pipe)
                p.register(w_pipe)
                # p.register(stdin_pipe)
                p.register(stdout_pipe)
                p.register(stderr_pipe)
                p.register(self.r_pipe)
                # p.register(self.w_pipe)
                p.register(sys.stdin.fileno())
                # p.register(sys.stdout.fileno())
                # p.register(sys.stderr.fileno())
                io_map = {r_pipe: self.w_pipe,
                          self.r_pipe: w_pipe,
                          sys.stdin.fileno(): stdin_pipe,
                          stdout_pipe: sys.stdout.fileno(),
                          stderr_pipe: sys.stderr.fileno()}
                while 1:
                    d = p.poll()
                    w_ev = [x for x in d if x[0] in w_fds]
                    m_ev = [x for x in d if x[0] in m_fds]
                    w_hup, w_read, _ = sort_fds_event(w_ev)
                    m_hup, m_read, _ = sort_fds_event(m_ev)
                    if m_hup:
                        time.sleep(0.1)
                    if w_hup:  # child process finished
                        for r in w_read:
                            data = os.read(r, 16384)
                            os.write(io_map[r], data)
                        break
                    for r in w_read:
                        data = os.read(r, 16384)
                        os.write(io_map[r], data)
                    for r in m_read:
                        data = os.read(r, 16384)
                        os.write(io_map[r], data)
                self.msg = ms.Messenger(ms.StdIOWrapperIn(self.r_pipe),
                                        ms.StdIOWrapperOut(self.w_pipe))
                self.msg.write_msg(CmdFinish())
                exit(0)
        else:  # main process open communication named pipes.
            self.w_pipe = os.open(self.w_path, os.O_WRONLY)
            self.r_pipe = os.open(self.r_path, os.O_RDONLY)
            self.stdout_pipe = os.open(self.stdout_path, os.O_RDONLY)
            self.stderr_pipe = os.open(self.stderr_path, os.O_RDONLY)
            self.stdin_pipe = os.open(self.stdin_path, os.O_WRONLY)
            self.msg = ms.Messenger(ms.StdIOWrapperIn(self.r_pipe),
                                    ms.StdIOWrapperOut(self.w_pipe))

    def work(self):
        """
        Wait for message from running child process
        """
        succ, msg = self.msg.read_msg()
        if isinstance(msg, CmdFinish):
            try:
                pid, _ = os.waitpid(msg.pid, 0)
            except OSError:
                pid = msg.pid
            if (succ is False or pid == msg.pid):
                self.basecmd._finished = True
                return True
            else:
                return False
        else:
            self.basecmd.results = msg

    def recover_paths(self):
        """
        Helper function for reconnect to daemon/nohup process.
        """
        self.stdin_path = os.path.join(self.basecmd.cmd_hash, "stdin")
        self.stdout_path = os.path.join(self.basecmd.cmd_hash, "stdout")
        self.stderr_path = os.path.join(self.basecmd.cmd_hash, "stderr")
        self.w_path = os.path.join(self.basecmd.cmd_hash, "results")
        self.r_path = os.path.join(self.basecmd.cmd_hash, "inputs")

    def recover_fds(self):
        """
        Helper function for reconnect to daemon/nohup process.
        """
        if self.r_pipe is None:
            self.recover_paths()
            self.w_pipe = os.open(self.w_path, os.O_WRONLY)
            self.r_pipe = os.open(self.r_path, os.O_RDONLY)
            self.stdin_pipe = os.open(self.stdin_path, os.O_WRONLY)
            self.stdout_pipe = os.open(self.stdout_path, os.O_RDONLY)
            self.stderr_pipe = os.open(self.stderr_path, os.O_RDONLY)
            self.msg = ms.Messenger(ms.StdIOWrapperIn(self.r_pipe),
                                    ms.StdIOWrapperOut(self.w_pipe))

    def finish(self, commander):
        """
        Remove cmd from commander commands on finish of process.
        """
        self.close_pipes()
        if self.basecmd.cmd_hash:
            clean_tmp_dir(self.basecmd.cmd_hash)
            self.basecmd.cmd_hash = None
        del commander.cmds[self.cmd_id]


class CommanderSlave(ms.Messenger):

    """
    Class commander slace is responsible for communication with commander
    master. It invoke commands to slave part and receive messages from them.
    For communication is used only stdin and stdout which are streams from
    slave part.
    """

    def __init__(self, stdin, stdout, o_stdout, o_stderr):
        super(CommanderSlave, self).__init__(stdin, stdout)
        self._exit = False
        self.cmds = {}
        self.globals = {}
        self.locals = {}
        self.o_stdout = o_stdout
        self.o_stderr = o_stderr

    def cmd_loop(self):
        """
        Wait for commands from master and receive results and outputs from
        commands.
        """
        try:
            while (not self._exit):
                stdios = [self.stdin, self.o_stdout, self.o_stderr]
                r_pipes = [cmd.r_pipe for cmd in self.cmds.values()
                           if cmd.r_pipe is not None]
                stdouts = [cmd.stdout_pipe for cmd in self.cmds.values()
                           if cmd.stdout_pipe is not None]
                stderrs = [cmd.stderr_pipe for cmd in self.cmds.values()
                           if cmd.stderr_pipe is not None]

                r, _, _ = select.select(stdios + r_pipes + stdouts + stderrs, [], [])

                if self.stdin in r:  # command from controller
                    cmd = CmdSlave(self.read_msg()[1])
                    self.cmds[cmd.cmd_id] = cmd
                    try:
                        cmd(self)
                        self.write_msg(cmd.basecmd)
                    except Exception:
                        err_msg = traceback.format_exc()
                        self.write_msg(remote_interface.CommanderError(err_msg))

                if self.o_stdout in r:  # Send message from stdout
                    msg = os.read(self.o_stdout, 16384)
                    self.write_msg(remote_interface.StdOut(msg))
                if self.o_stderr in r:  # Send message from stdout
                    msg = os.read(self.o_stderr, 16384)
                    self.write_msg(remote_interface.StdErr(msg))

                # test all commands for io
                for cmd in self.cmds.values():
                    if cmd.stdout_pipe in r:  # command stdout
                        data = os.read(cmd.stdout_pipe, 16384)
                        if data != "":  # pipe is not closed on another side.
                            self.write_msg(remote_interface.StdOut(data,
                                                                   cmd.cmd_id))
                        else:
                            os.close(cmd.stdout_pipe)
                            cmd.stdout_pipe = None
                    if cmd.stderr_pipe in r:  # command stderr
                        data = os.read(cmd.stderr_pipe, 16384)
                        if data != "":  # pipe is not closed on another side.
                            self.write_msg(remote_interface.StdErr(data,
                                                                   cmd.cmd_id))
                        else:
                            os.close(cmd.stderr_pipe)
                            cmd.stderr_pipe = None
                    if cmd.r_pipe in r:  # command results
                        if cmd.work():
                            cmd.finish(self)
                        self.write_msg(cmd.basecmd)
        except Exception:
            err_msg = traceback.format_exc()
            self.write_msg(remote_interface.CommanderError(err_msg))

    def _close_cmds_stdios(self, exclude_cmd):
        for cmd in self.cmds.values():
            if cmd is not exclude_cmd:
                cmd.close_pipes()


class CommanderSlaveCmds(CommanderSlave):

    """
    Class extends CommanderSlave and adds to them special commands like
    shell process, interactive python, send_msg to cmd.
    """

    def __init__(self, stdin, stdout, o_stdout, o_stderr):
        super(CommanderSlaveCmds, self).__init__(stdin, stdout,
                                                 o_stdout, o_stderr)

        while (1):
            succ, data = self.read_msg()
            if succ and data == "start":
                break
        self.write_msg("Started")

    def shell(self, cmd):
        """
        Starts shell process. Stdout is automatically copyed to basecmd.stdout

        :param cmd: Command which should be started.
        :return: basecmd with return code of cmd.
        """
        process = subprocess.Popen(cmd,
                                   shell=True,
                                   stdin=sys.stdin,
                                   stdout=sys.stdout,
                                   stderr=sys.stderr)

        return process.wait()

    def interactive(self):
        """
        Starts interactive python.
        """
        while 1:
            out = raw_input()
            if out == "":
                return
            try:
                exec out
            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                print "On Guest exception from: \n" + "".join(
                    traceback.format_exception(exc_type,
                                               exc_value,
                                               exc_traceback))
                print "FAIL: Guest command exception."

    def send_msg(self, msg, cmd_id):
        """
        Send msg to cmd with id == cmd_id

        :param msg: message passed to cmd over the stdin
        :type msg: str
        :param cmd_id: id of cmd.
        """
        os.write(self.cmds[cmd_id].stdin_pipe, msg)

    def register_cmd(self, basecmd, basecmd_cmd_id):
        """
        Second side of set_commander cmd from master. It register existing
        cmd to CommandSlave dict.

        :param basecmd: cmd which should be added to CommandSlave dict
        :type basecmd: BaseCmd
        :param basecmd_cmd_id: number under which should be stored
        :type basecmd_cmd_id: int
        """
        remote_interface.BaseCmd.single_cmd_id = basecmd_cmd_id
        cmd = CmdSlave(basecmd)
        self.cmds[basecmd.cmd_id] = cmd
        if cmd.basecmd.cmd_hash is not None:
            cmd.recover_fds()
        return basecmd

    def add_function(self, f_code):
        """
        Adds function to client code.

        :param f_code: Code of function.
        :type f_code: str.
        """
        exec(f_code, globals(), globals())

    def copy_file(self, name, path, content):
        """
        Really naive implementation of copping files. Should be used only for
        short files.
        """
        f = open(os.path.join(path, name), "w")
        f.write(content)
        f.close()

    def import_src(self, name, path=None):
        """
        Import file to running python session.
        """
        if path:
            if path not in sys.path:
                sys.path.append(path)
        mod = __import__(name, globals(), locals())
        globals()[name] = mod
        sys.modules[name] = mod

    def exit(self):
        """
        Method for killing command slave.
        """
        self._exit = True
        return "bye"


def remote_agent(in_stream_cls, out_stream_cls):
    """
    Connect file descriptors to right pipe and start slave command loop.
    When something happend it raise exception which could be caught by cmd
    master.

    :params in_stream_cls: Class encapsulated input stream.
    :params out_stream_cls: Class encapsulated output stream.
    """
    try:
        fd_stdout = sys.stdout.fileno()
        fd_stderr = sys.stderr.fileno()
        fd_stdin = sys.stdin.fileno()
        soutr, soutw = os.pipe()
        serrr, serrw = os.pipe()
        sys.stdout = os.fdopen(soutw, 'w', 0)
        sys.stderr = os.fdopen(serrw, 'w', 0)
        os.write(fd_stdout, "#")

        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

        w_stdin = None
        w_stdout = out_stream_cls(fd_stdout)
        w_stdin = in_stream_cls(fd_stdin)

        cmd = CommanderSlaveCmds(w_stdin,
                                 w_stdout,
                                 soutr,
                                 serrr)

        cmd.cmd_loop()
    except SystemExit:
        pass
    except:
        e = traceback.format_exc()
        sys.stderr.write(e)
        # traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "agent":
            remote_agent(ms.StdIOWrapperIn, ms.StdIOWrapperOut)
        elif sys.argv[1] == "agent_base64":
            remote_agent(ms.StdIOWrapperInBase64, ms.StdIOWrapperOutBase64)
