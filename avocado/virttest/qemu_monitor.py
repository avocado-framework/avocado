"""
Interfaces to the QEMU monitor.

:copyright: 2008-2010 Red Hat Inc.
"""

import socket
import time
import threading
import logging
import select
import re
import os
import utils_misc
import passfd_setup
from autotest.client.shared import utils
try:
    import json
except ImportError:
    logging.warning("Could not import json module. "
                    "QMP monitor functionality disabled.")


class MonitorError(Exception):
    pass


class MonitorConnectError(MonitorError):

    def __init__(self, monitor_name):
        MonitorError.__init__(self)
        self.monitor_name = monitor_name

    def __str__(self):
        return "Could not connect to monitor '%s'" % self.monitor_name


class MonitorSocketError(MonitorError):

    def __init__(self, msg, e):
        Exception.__init__(self, msg, e)
        self.msg = msg
        self.e = e

    def __str__(self):
        return "%s    (%s)" % (self.msg, self.e)


class MonitorLockError(MonitorError):
    pass


class MonitorProtocolError(MonitorError):
    pass


class MonitorNotSupportedError(MonitorError):
    pass


class MonitorNotSupportedCmdError(MonitorNotSupportedError):

    def __init__(self, monitor, cmd):
        MonitorError.__init__(self)
        self.monitor = monitor
        self.cmd = cmd

    def __str__(self):
        return ("Not supported cmd '%s' in monitor '%s'" %
                (self.cmd, self.monitor))


class QMPCmdError(MonitorError):

    def __init__(self, cmd, qmp_args, data):
        MonitorError.__init__(self, cmd, qmp_args, data)
        self.cmd = cmd
        self.qmp_args = qmp_args
        self.data = data

    def __str__(self):
        return ("QMP command %r failed    (arguments: %r,    "
                "error message: %r)" % (self.cmd, self.qmp_args, self.data))


def get_monitor_filename(vm, monitor_name):
    """
    Return the filename corresponding to a given monitor name.

    :param vm: The VM object which has the monitor.
    :param monitor_name: The monitor name.
    :return: The string of socket file name for qemu monitor.
    """
    return "/tmp/monitor-%s-%s" % (monitor_name, vm.instance)


def get_monitor_filenames(vm):
    """
    Return a list of all monitor filenames (as specified in the VM's
    params).

    :param vm: The VM object which has the monitors.
    """
    return [get_monitor_filename(vm, m) for m in vm.params.objects("monitors")]


def create_monitor(vm, monitor_name, monitor_params):
    """
    Create monitor object and connect to the monitor socket.

    :param vm: The VM object which has the monitor.
    :param monitor_name: The name of this monitor object.
    :param monitor_params: The dict for creating this monitor object.
    """
    monitor_creator = HumanMonitor
    if monitor_params.get("monitor_type") == "qmp":
        monitor_creator = QMPMonitor
        if not utils_misc.qemu_has_option("qmp", vm.qemu_binary):
            # Add a "human" monitor on non-qmp version of qemu.
            logging.warn("QMP monitor is unsupported by this version of qemu,"
                         " creating human monitor instead.")
            monitor_creator = HumanMonitor

    monitor_filename = get_monitor_filename(vm, monitor_name)
    logging.info("Connecting to monitor '%s'", monitor_name)
    monitor = monitor_creator(vm, monitor_name, monitor_filename)
    monitor.verify_responsive()

    return monitor


def wait_for_create_monitor(vm, monitor_name, monitor_params, timeout):
    """
    Wait for the progress of creating monitor object. This function will
    retry to create the Monitor object until timeout.

    :param vm: The VM object which has the monitor.
    :param monitor_name: The name of this monitor object.
    :param monitor_params: The dict for creating this monitor object.
    :param timeout: Time to wait for creating this monitor object.
    """
    # Wait for monitor connection to succeed
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            return create_monitor(vm, monitor_name, monitor_params)
        except MonitorError, e:
            logging.warn(e)
            time.sleep(1)
    else:
        raise MonitorConnectError(monitor_name)


class Monitor:

    """
    Common code for monitor classes.
    """

    ACQUIRE_LOCK_TIMEOUT = 20
    DATA_AVAILABLE_TIMEOUT = 0
    CONNECT_TIMEOUT = 30

    def __init__(self, vm, name, filename):
        """
        Initialize the instance.

        :param vm: The VM which this monitor belongs to.
        :param name: Monitor identifier (a string)
        :param filename: Monitor socket filename

        :raise MonitorConnectError: Raised if the connection fails
        """
        self.vm = vm
        self.name = name
        self.filename = filename
        self._lock = threading.RLock()
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.settimeout(self.CONNECT_TIMEOUT)
        self._passfd = None
        self._supported_cmds = []
        self.debug_log = False
        self.log_file = os.path.basename(self.filename + ".log")

        try:
            self._socket.connect(filename)
        except socket.error, details:
            raise MonitorConnectError("Could not connect to monitor socket: %s"
                                      % details)

    def __del__(self):
        # Automatically close the connection when the instance is garbage
        # collected
        self._close_sock()
        utils_misc.close_log_file(self.log_file)

    # The following two functions are defined to make sure the state is set
    # exclusively by the constructor call as specified in __getinitargs__().
    def __getstate__(self):
        pass

    def __setstate__(self, state):
        pass

    def __getinitargs__(self):
        # Save some information when pickling -- will be passed to the
        # constructor upon unpickling
        return self.vm, self.name, self.filename, True

    def _close_sock(self):
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        self._socket.close()

    def _acquire_lock(self, timeout=ACQUIRE_LOCK_TIMEOUT):
        end_time = time.time() + timeout
        while time.time() < end_time:
            if self._lock.acquire(False):
                return True
            time.sleep(0.05)
        return False

    def _data_available(self, timeout=DATA_AVAILABLE_TIMEOUT):
        timeout = max(0, timeout)
        try:
            return bool(select.select([self._socket], [], [], timeout)[0])
        except socket.error, e:
            raise MonitorSocketError("Verifying data on monitor socket", e)

    def _recvall(self):
        s = ""
        while self._data_available():
            try:
                data = self._socket.recv(1024)
            except socket.error, e:
                raise MonitorSocketError("Could not receive data from monitor",
                                         e)
            if not data:
                break
            s += data
        return s

    def _has_command(self, cmd):
        """
        Check wheter kvm monitor support 'cmd'.

        :param cmd: command string which will be checked.

        :return: True if cmd is supported, False if not supported.
        """
        if cmd and cmd in self._supported_cmds:
            return True
        return False

    def _log_command(self, cmd, debug=True, extra_str=""):
        """
        Print log message beening sent.

        :param cmd: Command string.
        :param debug: Whether to print the commands.
        :param extra_str: Extra string would be printed in log.
        """
        if self.debug_log or debug:
            logging.debug("(monitor %s) Sending command '%s' %s",
                          self.name, cmd, extra_str)

    def _log_lines(self, log_str):
        """
        Record monitor cmd/output in log file.
        """
        try:
            for l in log_str.splitlines():
                utils_misc.log_line(self.log_file, l)
        except Exception:
            pass

    def correct(self, cmd):
        """
        Automatic conversion "-" and "_" in commands if the translate command
        is supported commands;
        """
        def translate(cmd):
            return "-".join(re.split("[_-]", cmd))

        if not self._has_command(cmd):
            for _cmd in self._supported_cmds:
                if translate(_cmd) == translate(cmd):
                    logging.info("Convert command %s -> %s", cmd, _cmd)
                    return _cmd
        return cmd

    def is_responsive(self):
        """
        Return True iff the monitor is responsive.
        """
        try:
            self.verify_responsive()
            return True
        except MonitorError:
            return False

    def verify_supported_cmd(self, cmd):
        """
        Verify whether cmd is supported by monitor. If not, raise a
        MonitorNotSupportedCmdError Exception.

        :param cmd: The cmd string need to verify.
        """
        if not self._has_command(cmd):
            raise MonitorNotSupportedCmdError(self.name, cmd)

    # Methods that may be implemented by subclasses:

    def human_monitor_cmd(self, cmd="", timeout=None,
                          debug=True, fd=None):
        """
        Send HMP command

        This method allows code to send HMP commands without the need to check
        if the monitor is QMPMonitor or HumanMonitor.

        :param cmd: human monitor command.
        :param timeout: Time duration to wait for response
        :param debug: Whether to print the commands being sent and responses
        :param fd: file object or file descriptor to pass

        :return: The response to the command
        """
        raise NotImplementedError

    # Methods that should work on both classes, as long as human_monitor_cmd()
    # works:
    re_numa_nodes = re.compile(r"^([0-9]+) nodes$", re.M)
    re_numa_node_info = re.compile(r"^node ([0-9]+) (cpus|size): (.*)$", re.M)

    @classmethod
    def parse_info_numa(cls, r):
        """
        Parse 'info numa' output

        See info_numa() for information about the return value.
        """

        nodes = cls.re_numa_nodes.search(r)
        if nodes is None:
            raise Exception(
                "Couldn't get number of nodes from 'info numa' output")
        nodes = int(nodes.group(1))

        data = [[0, set()] for i in range(nodes)]
        for nodenr, field, value in cls.re_numa_node_info.findall(r):
            nodenr = int(nodenr)
            if nodenr > nodes:
                raise Exception(
                    "Invalid node number on 'info numa' output: %d", nodenr)
            if field == 'size':
                if not value.endswith(' MB'):
                    raise Exception("Unexpected size value: %s", value)
                megabytes = int(value[:-3])
                data[nodenr][0] = megabytes
            elif field == 'cpus':
                cpus = set([int(v) for v in value.split()])
                data[nodenr][1] = cpus
        data = [tuple(i) for i in data]
        return data

    def info_numa(self):
        """
        Run 'info numa' command and parse returned information

        :return: An array of (ram, cpus) tuples, where ram is the RAM size in
                 MB and cpus is a set of CPU numbers
        """
        r = self.human_monitor_cmd("info numa")
        return self.parse_info_numa(r)

    def info(self, what, debug=True):
        """
        Request info about something and return the response.
        """
        raise NotImplementedError

    def info_block(self, debug=True):
        """
        Request info about blocks and return dict of parsed results
        :return: Dict of disk parameters
        """
        info = self.info('block', debug)
        if isinstance(info, str):
            try:
                return self._parse_info_block_old(info)
            except ValueError:
                return self._parse_info_block_1_5(info)
        else:
            return self._parse_info_block_qmp(info)

    @staticmethod
    def _parse_info_block_old(info):
        """
        Parse output of "info block" into dict of disk params (qemu < 1.5.0)
        """
        blocks = {}
        info = info.split('\n')
        for line in info:
            if not line.strip():
                continue
            line = line.split(':', 1)
            name = line[0].strip()
            blocks[name] = {}
            if line[1].endswith('[not inserted]'):
                blocks[name]['not-inserted'] = 1
                line[1] = line[1][:-14]
            for _ in line[1].strip().split(' '):
                (prop, value) = _.split('=', 1)
                if value.isdigit():
                    value = int(value)
                blocks[name][prop] = value
        return blocks

    @staticmethod
    def _parse_info_block_1_5(info):
        """
        Parse output of "info block" into dict of disk params (qemu >= 1.5.0)
        """
        blocks = {}
        info = info.split('\n')
        for line in info:
            if not line.strip():
                continue
            if not line.startswith(' '):   # new block device
                line = line.split(':', 1)
                name = line[0].strip()
                line = line[1][1:]
                blocks[name] = {}
                if line == "[not inserted]":
                    blocks[name]['not-inserted'] = 1
                    continue
                line = line.rsplit(' (', 1)
                if len(line) == 1:       # disk_name
                    blocks[name]['file'] = line
                else:       # disk_name (options)
                    blocks[name]['file'] = line[0]
                    options = (_.strip() for _ in line[1][:-1].split(','))
                    _ = False
                    for option in options:
                        if not _:   # First argument is driver (qcow2, raw, ..)
                            blocks[name]['drv'] = option
                            _ = True
                        elif option == 'read-only':
                            blocks[name]['ro'] = 1
                        elif option == 'encrypted':
                            blocks[name]['encrypted'] = 1
                        else:
                            err = ("_parse_info_block_1_5 got option '%s' "
                                   "which is not yet mapped in autotest. "
                                   "Please contact developers on github.com/"
                                   "autotest." % option)
                            raise NotImplementedError(err)
            else:
                try:
                    option, line = line.split(':', 1)
                    option, line = option.strip(), line.strip()
                    if option == "Backing file":
                        line = line.rsplit(' (chain depth: ')
                        blocks[name]['backing_file'] = line[0]
                        blocks[name]['backing_file_depth'] = int(line[1][:-1])
                    elif option == "Removable device":
                        blocks[name]['removable'] = 1
                        if 'not locked' not in line:
                            blocks[name]['locked'] = 1
                        if 'try open' in line:
                            blocks[name]['try-open'] = 1
                except ValueError:
                    continue

        return blocks

    @staticmethod
    def _parse_info_block_qmp(info):
        """
        Parse output of "query block" into dict of disk params
        """
        blocks = {}
        for item in info:
            if not item.get('device'):
                raise ValueError("Incorrect QMP respone, device not set in"
                                 "info block: %s" % info)
            name = item.pop('device')
            blocks[name] = {}
            if 'inserted' not in item:
                blocks[name]['not-inserted'] = True
            else:
                for key, value in item.pop('inserted', {}).iteritems():
                    blocks[name][key] = value
            for key, value in item.iteritems():
                blocks[name][key] = value
        return blocks

    def close(self):
        """
        Close the connection to the monitor and its log file.
        """
        self._close_sock()
        utils_misc.close_log_file(self.log_file)


class HumanMonitor(Monitor):

    """
    Wraps "human monitor" commands.
    """

    PROMPT_TIMEOUT = 60
    CMD_TIMEOUT = 120

    def __init__(self, vm, name, filename, suppress_exceptions=False):
        """
        Connect to the monitor socket and find the (qemu) prompt.

        :param vm: The VM which this monitor belongs to.
        :param name: Monitor identifier (a string)
        :param filename: Monitor socket filename

        :raise MonitorConnectError: Raised if the connection fails and
                suppress_exceptions is False
        :raise MonitorProtocolError: Raised if the initial (qemu) prompt isn't
                found and suppress_exceptions is False
        :note: Other exceptions may be raised.  See cmd()'s
                docstring.
        """
        try:
            Monitor.__init__(self, vm, name, filename)

            self.protocol = "human"

            # Find the initial (qemu) prompt
            s, o = self._read_up_to_qemu_prompt()
            if not s:
                raise MonitorProtocolError("Could not find (qemu) prompt "
                                           "after connecting to monitor. "
                                           "Output so far: %r" % o)

            self._get_supported_cmds()

        except MonitorError, e:
            self._close_sock()
            if suppress_exceptions:
                logging.warn(e)
            else:
                raise

    # Private methods
    def _read_up_to_qemu_prompt(self, timeout=PROMPT_TIMEOUT):
        s = ""
        end_time = time.time() + timeout
        while self._data_available(end_time - time.time()):
            data = self._recvall()
            if not data:
                break
            s += data
            try:
                lines = s.splitlines()
                # Sometimes the qemu monitor lacks a line break before the
                # qemu prompt, so we have to be less exigent:
                if lines[-1].split()[-1].endswith("(qemu)"):
                    self._log_lines("\n".join(lines[1:]))
                    return True, "\n".join(lines[:-1])
            except IndexError:
                continue
        if s:
            try:
                self._log_lines(s.splitlines()[1:])
            except IndexError:
                pass
        return False, "\n".join(s.splitlines())

    def _send(self, cmd):
        """
        Send a command without waiting for output.

        :param cmd: Command to send
        :raise MonitorLockError: Raised if the lock cannot be acquired
        :raise MonitorSocketError: Raised if a socket error occurs
        """
        if not self._acquire_lock():
            raise MonitorLockError("Could not acquire exclusive lock to send "
                                   "monitor command '%s'" % cmd)

        try:
            try:
                self._socket.sendall(cmd + "\n")
                self._log_lines(cmd)
            except socket.error, e:
                raise MonitorSocketError("Could not send monitor command %r" %
                                         cmd, e)

        finally:
            self._lock.release()

    def _get_supported_cmds(self):
        """
        Get supported human monitor cmds list.
        """
        cmds = self.cmd("help", debug=False)
        if cmds:
            cmd_list = re.findall("^(.*?) ", cmds, re.M)
            self._supported_cmds = [c for c in cmd_list if c]

        if not self._supported_cmds:
            logging.warn("Could not get supported monitor cmds list")

    def _log_response(self, cmd, resp, debug=True):
        """
        Print log message for monitor cmd's response.

        :param cmd: Command string.
        :param resp: Response from monitor command.
        :param debug: Whether to print the commands.
        """
        if self.debug_log or debug:
            logging.debug("(monitor %s) Response to '%s'", self.name, cmd)
            for l in resp.splitlines():
                logging.debug("(monitor %s)    %s", self.name, l)

    # Public methods
    def cmd(self, cmd, timeout=CMD_TIMEOUT, debug=True, fd=None):
        """
        Send command to the monitor.

        :param cmd: Command to send to the monitor
        :param timeout: Time duration to wait for the (qemu) prompt to return
        :param debug: Whether to print the commands being sent and responses
        :return: Output received from the monitor
        :raise MonitorLockError: Raised if the lock cannot be acquired
        :raise MonitorSocketError: Raised if a socket error occurs
        :raise MonitorProtocolError: Raised if the (qemu) prompt cannot be
                found after sending the command
        """
        self._log_command(cmd, debug)
        if not self._acquire_lock():
            raise MonitorLockError("Could not acquire exclusive lock to send "
                                   "monitor command '%s'" % cmd)

        try:
            # Read any data that might be available
            self._recvall()
            if fd is not None:
                if self._passfd is None:
                    self._passfd = passfd_setup.import_passfd()
                # If command includes a file descriptor, use passfd module
                self._passfd.sendfd(self._socket, fd, "%s\n" % cmd)
            else:
                # Send command
                if debug:
                    logging.debug("Send command: %s" % cmd)
                self._send(cmd)
            # Read output
            s, o = self._read_up_to_qemu_prompt(timeout)
            # Remove command echo from output
            o = "\n".join(o.splitlines()[1:])
            # Report success/failure
            if s:
                if o:
                    self._log_response(cmd, o, debug)
                return o
            else:
                msg = ("Could not find (qemu) prompt after command '%s'. "
                       "Output so far: %r" % (cmd, o))
                raise MonitorProtocolError(msg)

        finally:
            self._lock.release()

    def human_monitor_cmd(self, cmd="", timeout=CMD_TIMEOUT,
                          debug=True, fd=None):
        """
        Send human monitor command directly

        :param cmd: human monitor command.
        :param timeout: Time duration to wait for response
        :param debug: Whether to print the commands being sent and responses
        :param fd: file object or file descriptor to pass

        :return: The response to the command
        """
        return self.cmd(cmd, timeout, debug, fd)

    def verify_responsive(self):
        """
        Make sure the monitor is responsive by sending a command.
        """
        self.cmd("info status", debug=False)

    def get_status(self):
        return self.cmd("info status", debug=False)

    def verify_status(self, status):
        """
        Verify VM status

        :param status: Optional VM status, 'running' or 'paused'
        :return: return True if VM status is same as we expected
        """
        return (status in self.get_status())

    # Command wrappers
    # Notes:
    # - All of the following commands raise exceptions in a similar manner to
    #   cmd().
    # - A command wrapper should use self._has_command if it requires
    #    information about the monitor's capabilities.
    def send_args_cmd(self, cmdlines, timeout=CMD_TIMEOUT, convert=True):
        """
        Send a command with/without parameters and return its output.
        Have same effect with cmd function.
        Implemented under the same name for both the human and QMP monitors.
        Command with parameters should in following format e.g.:
        'memsave val=0 size=10240 filename=memsave'
        Command without parameter: 'sendkey ctrl-alt-f1'

        :param cmdlines: Commands send to qemu which is separated by ";". For
                         command with parameters command should send in a string
                         with this format:
                         $command $arg_name=$arg_value $arg_name=$arg_value
        :param timeout: Time duration to wait for (qemu) prompt after command
        :param convert: If command need to convert. For commands such as:
                        $command $arg_value
        :return: The output of the command
        :raise MonitorLockError: Raised if the lock cannot be acquired
        :raise MonitorSendError: Raised if the command cannot be sent
        :raise MonitorProtocolError: Raised if the (qemu) prompt cannot be
                found after sending the command
        """
        cmd_output = []
        for cmdline in cmdlines.split(";"):
            if not convert:
                return self.cmd(cmdline, timeout)
            if "=" in cmdline:
                command = cmdline.split()[0]
                cmdargs = " ".join(cmdline.split()[1:]).split(",")
                for arg in cmdargs:
                    value = "=".join(arg.split("=")[1:])
                    if arg.split("=")[0] == "cert-subject":
                        value = value.replace('/', ',')
                    command += " " + value
            else:
                command = cmdline
            cmd_output.append(self.cmd(command, timeout))
        if len(cmd_output) == 1:
            return cmd_output[0]
        return cmd_output

    def quit(self):
        """
        Send "quit" without waiting for output.
        """
        self._send("quit")

    def info(self, what, debug=True):
        """
        Request info about something and return the output.
        :param debug: Whether to print the commands being sent and responses
        """
        return self.cmd("info %s" % what, debug=debug)

    def query(self, what):
        """
        Alias for info.
        """
        return self.info(what)

    def screendump(self, filename, debug=True):
        """
        Request a screendump.

        :param filename: Location for the screendump
        :return: The command's output
        """
        return self.cmd(cmd="screendump %s" % filename, debug=debug)

    def set_link(self, name, up):
        """
        Set link up/down.

        :param name: Link name
        :param up: Bool value, True=set up this link, False=Set down this link
        :return: The response to the command
        """
        set_link_cmd = "set_link"

        # set_link in RHEL5 host use "up|down" instead of "on|off" which is
        # used in RHEL6 host and Fedora host. So here find out the string
        # this monitor accept.
        o = self.cmd("help %s" % set_link_cmd)
        try:
            on_str, off_str = re.findall("(\w+)\|(\w+)", o)[0]
        except IndexError:
            # take a default value if can't get on/off string from monitor.
            on_str, off_str = "on", "off"

        status = off_str
        if up:
            status = on_str
        return self.cmd("%s %s %s" % (set_link_cmd, name, status))

    def live_snapshot(self, device, snapshot_file, snapshot_format="qcow2"):
        """
        Take a live disk snapshot.

        :param device: device id of base image
        :param snapshot_file: image file name of snapshot
        :param snapshot_format: image format of snapshot

        :return: The response to the command
        """
        cmd = ("snapshot_blkdev %s %s %s" %
               (device, snapshot_file, snapshot_format))
        return self.cmd(cmd)

    def block_stream(self, device, speed=None, base=None,
                     cmd="block_stream", correct=True):
        """
        Start block-stream job;

        :param device: device ID
        :param speed: int type, lmited speed(B/s)
        :param base: base file
        :param correct: auto correct command, correct by default

        :return: The command's output
        """
        if correct:
            cmd = self.correct(cmd)
        self.verify_supported_cmd(cmd)
        cmd += " %s" % device
        if speed is not None:
            cmd += " %sB" % speed
        if base:
            cmd += " %s" % base
        return self.cmd(cmd)

    def set_block_job_speed(self, device, speed=0,
                            cmd="block_job_set_speed", correct=True):
        """
        Set limited speed for runnig job on the device

        :param device: device ID
        :param speed: int type, limited speed(B/s)
        :param correct: auto correct command, correct by default

        :return: The command's output
        """
        if correct:
            cmd = self.correct(cmd)
        self.verify_supported_cmd(cmd)
        cmd += " %s %sB" % (device, speed)
        return self.cmd(cmd)

    def cancel_block_job(self, device, cmd="block_job_cancel", correct=True):
        """
        Cancel running block stream/mirror job on the device

        :param device: device ID
        :param correct: auto correct command, correct by default

        :return: The command's output
        """
        if correct:
            cmd = self.correct(cmd)
        self.verify_supported_cmd(cmd)
        cmd += " %s" % device
        return self.send_args_cmd(cmd)

    def query_block_job(self, device):
        """
        Get block job status on the device

        :param device: device ID

        :return: dict about job info, return empty dict if no active job
        """
        job = dict()
        output = str(self.info("block-jobs"))
        for line in output.split("\n"):
            if "No" in re.match("\w+", output).group(0):
                continue
            if device in line:
                if "Streaming" in re.match("\w+", output).group(0):
                    job["type"] = "stream"
                else:
                    job["type"] = "mirror"
                job["device"] = device
                job["offset"] = int(re.findall("\d+", output)[-3])
                job["len"] = int(re.findall("\d+", output)[-2])
                job["speed"] = int(re.findall("\d+", output)[-1])
                break
        return job

    def get_backingfile(self, device):
        """
        Return "backing_file" path of the device

        :param device: device ID

        :return: string, backing_file path
        """
        backing_file = None
        block_info = self.query("block")
        try:
            pattern = "%s:.*backing_file=([^\s]*)" % device
            backing_file = re.search(pattern, block_info, re.M).group(1)
        except Exception:
            pass
        return backing_file

    def block_mirror(self, device, target, speed, sync, format, mode,
                     cmd="drive_mirror", correct=True):
        """
        Start mirror type block device copy job

        :param device: device ID
        :param target: target image
        :param speed: limited speed, unit is B/s
        :param sync: full copy to target image(unsupport in human monitor)
        :param mode: target image create mode, 'absolute-paths' or 'existing'
        :param format: target image format
        :param cmd: block mirror command
        :param correct: auto correct command, correct by default

        :return: The command's output
        """
        if correct:
            cmd = self.correct(cmd)
        self.verify_supported_cmd(cmd)
        args = " %s %s %s" % (device, target, format)
        info = str(self.cmd("help %s" % cmd))
        if (mode == "existing") and "-n" in info:
            args = "-n %s" % args
        if (sync == "full") and "-f" in info:
            args = "-f %s" % args
        if (speed is not None) and ("speed" in info):
            args = "%s %s" % (args, speed)
        cmd = "%s %s" % (cmd, args)
        return self.cmd(cmd)

    def block_reopen(self, device, new_image_file, image_format,
                     cmd="block_job_complete", correct=True):
        """
        Reopen new target image

        :param device: device ID
        :param new_image_file: new image file name
        :param image_format: new image file format
        :param cmd: image reopen command
        :param correct: auto correct command, correct by default

        :return: The command's output
        """
        if correct:
            cmd = self.correct(cmd)
        self.verify_supported_cmd(cmd)
        args = "%s" % device
        info = str(self.cmd("help %s" % cmd))
        if "format" in info:
            args += " %s %s" % (new_image_file, image_format)
        cmd = "%s %s" % (cmd, args)
        return self.cmd(cmd)

    def migrate(self, uri, full_copy=False, incremental_copy=False, wait=False):
        """
        Migrate.

        :param uri: destination URI
        :param full_copy: If true, migrate with full disk copy
        :param incremental_copy: If true, migrate with incremental disk copy
        :param wait: If true, wait for completion
        :return: The command's output
        """
        cmd = "migrate"
        if not wait:
            cmd += " -d"
        if full_copy:
            cmd += " -b"
        if incremental_copy:
            cmd += " -i"
        cmd += " %s" % uri
        return self.cmd(cmd)

    def migrate_set_speed(self, value):
        """
        Set maximum speed (in bytes/sec) for migrations.

        :param value: Speed in bytes/sec
        :return: The command's output
        """
        return self.cmd("migrate_set_speed %s" % value)

    def migrate_set_downtime(self, value):
        """
        Set maximum tolerated downtime (in seconds) for migration.

        :param value: maximum downtime (in seconds)
        :return: The command's output
        """
        return self.cmd("migrate_set_downtime %s" % value)

    def sendkey(self, keystr, hold_time=1):
        """
        Send key combination to VM.

        :param keystr: Key combination string
        :param hold_time: Hold time in ms (should normally stay 1 ms)
        :return: The command's output
        """
        return self.cmd("sendkey %s %s" % (keystr, hold_time))

    def mouse_move(self, dx, dy):
        """
        Move mouse.

        :param dx: X amount
        :param dy: Y amount
        :return: The command's output
        """
        return self.cmd("mouse_move %s %s" % (dx, dy))

    def mouse_button(self, state):
        """
        Set mouse button state.

        :param state: Button state (1=L, 2=M, 4=R)
        :return: The command's output
        """
        return self.cmd("mouse_button %s" % state)

    def getfd(self, fd, name):
        """
        Receives a file descriptor

        :param fd: File descriptor to pass to QEMU
        :param name: File descriptor name (internal to QEMU)
        :return: The command's output
        """
        return self.cmd("getfd %s" % name, fd=fd)

    def system_wakeup(self):
        """
        Wakeup suspended guest.
        """
        cmd = "system_wakeup"
        self.verify_supported_cmd(cmd)
        return self.cmd(cmd)

    def nmi(self):
        """
        Inject a NMI on all guest's CPUs.
        """
        return self.cmd("nmi")

    def block_resize(self, device, size):
        """
        Resize the block device size

        :param device: Block device name
        :param size: Block device size need to set to. To keep the same with
                     qmp monitor will use bytes as unit for the block size
        :return: Command output
        """
        size = int(size) / 1024 / 1024
        cmd = "block_resize device=%s,size=%s" % (device, size)
        return self.send_args_cmd(cmd)

    def eject_cdrom(self, device, force=False):
        """
        Eject media of cdrom and open cdrom door;
        """
        cmd = "eject"
        self.verify_supported_cmd(cmd)
        if force:
            cmd += " -f "
        cmd += " %s" % device
        return self.cmd(cmd)

    def change_media(self, device, target):
        """
        Change media of cdrom of drive;
        """
        cmd = "change"
        self.verify_supported_cmd(cmd)
        cmd += " %s %s" % (device, target)
        return self.cmd(cmd)


class QMPMonitor(Monitor):

    """
    Wraps QMP monitor commands.
    """

    READ_OBJECTS_TIMEOUT = 5
    CMD_TIMEOUT = 120
    RESPONSE_TIMEOUT = 120
    PROMPT_TIMEOUT = 60

    def __init__(self, vm, name, filename, suppress_exceptions=False):
        """
        Connect to the monitor socket, read the greeting message and issue the
        qmp_capabilities command.  Also make sure the json module is available.

        :param vm: The VM which this monitor belongs to.
        :param name: Monitor identifier (a string)
        :param filename: Monitor socket filename

        :raise MonitorConnectError: Raised if the connection fails and
                suppress_exceptions is False
        :raise MonitorProtocolError: Raised if the no QMP greeting message is
                received and suppress_exceptions is False
        :raise MonitorNotSupportedError: Raised if json isn't available and
                suppress_exceptions is False
        :note: Other exceptions may be raised if the qmp_capabilities command
                fails.  See cmd()'s docstring.
        """
        try:
            Monitor.__init__(self, vm, name, filename)

            self.protocol = "qmp"
            self._greeting = None
            self._events = []
            self._supported_hmp_cmds = []

            # Make sure json is available
            try:
                json
            except NameError:
                raise MonitorNotSupportedError("QMP requires the json module "
                                               "(Python 2.6 and up)")

            # Read greeting message
            end_time = time.time() + 20
            output_str = ""
            while time.time() < end_time:
                for obj in self._read_objects():
                    output_str += str(obj)
                    if "QMP" in obj:
                        self._greeting = obj
                        break
                if self._greeting:
                    break
                time.sleep(0.1)
            else:
                raise MonitorProtocolError("No QMP greeting message received."
                                           " Output so far: %s" % output_str)

            # Issue qmp_capabilities
            self.cmd("qmp_capabilities")

            self._get_supported_cmds()
            self._get_supported_hmp_cmds()

        except MonitorError, e:
            self._close_sock()
            if suppress_exceptions:
                logging.warn(e)
            else:
                raise

    # Private methods
    def _build_cmd(self, cmd, args=None, q_id=None):
        obj = {"execute": cmd}
        if args is not None:
            obj["arguments"] = args
        if q_id is not None:
            obj["id"] = q_id
        return obj

    def _read_objects(self, timeout=READ_OBJECTS_TIMEOUT):
        """
        Read lines from the monitor and try to decode them.
        Stop when all available lines have been successfully decoded, or when
        timeout expires.  If any decoded objects are asynchronous events, store
        them in self._events.  Return all decoded objects.

        :param timeout: Time to wait for all lines to decode successfully
        :return: A list of objects
        """
        if not self._data_available():
            return []
        s = ""
        end_time = time.time() + timeout
        while self._data_available(end_time - time.time()):
            s += self._recvall()
            # Make sure all lines are decodable
            for line in s.splitlines():
                if line:
                    try:
                        json.loads(line)
                    except Exception:
                        # Found an incomplete or broken line -- keep reading
                        break
            else:
                # All lines are OK -- stop reading
                break
        # Decode all decodable lines
        objs = []
        for line in s.splitlines():
            try:
                objs += [json.loads(line)]
                self._log_lines(line)
            except Exception:
                pass
        # Keep track of asynchronous events
        self._events += [obj for obj in objs if "event" in obj]
        return objs

    def _send(self, data):
        """
        Send raw data without waiting for response.

        :param data: Data to send
        :raise MonitorSocketError: Raised if a socket error occurs
        """
        try:
            self._socket.sendall(data)
            self._log_lines(str(data))
        except socket.error, e:
            raise MonitorSocketError("Could not send data: %r" % data, e)

    def _get_response(self, q_id=None, timeout=RESPONSE_TIMEOUT):
        """
        Read a response from the QMP monitor.

        :param id: If not None, look for a response with this id
        :param timeout: Time duration to wait for response
        :return: The response dict, or None if none was found
        """
        end_time = time.time() + timeout
        while self._data_available(end_time - time.time()):
            for obj in self._read_objects():
                if isinstance(obj, dict):
                    if q_id is not None and obj.get("id") != q_id:
                        continue
                    if "return" in obj or "error" in obj:
                        return obj

    def _get_supported_cmds(self):
        """
        Get supported qmp cmds list.
        """
        cmds = self.cmd("query-commands", debug=False)
        if cmds:
            self._supported_cmds = [n["name"] for n in cmds if
                                    n.has_key("name")]

        if not self._supported_cmds:
            logging.warn("Could not get supported monitor cmds list")

    def _get_supported_hmp_cmds(self):
        """
        Get supported human monitor cmds list.
        """
        cmds = self.human_monitor_cmd("help", debug=False)
        if cmds:
            cmd_list = re.findall(
                r"(?:^\w+\|(\w+)\s)|(?:^(\w+?)\s)", cmds, re.M)
            self._supported_hmp_cmds = [(i + j) for i, j in cmd_list if i or j]

        if not self._supported_cmds:
            logging.warn("Could not get supported monitor cmds list")

    def _has_hmp_command(self, cmd):
        """
        Check wheter monitor support hmp 'cmd'.

        :param cmd: command string which will be checked.

        :return: True if cmd is supported, False if not supported.
        """
        if cmd and cmd in self._supported_hmp_cmds:
            return True
        return False

    def verify_supported_hmp_cmd(self, cmd):
        """
        Verify whether cmd is supported by hmp monitor.
        If not, raise a MonitorNotSupportedCmdError Exception.

        :param cmd: The cmd string need to verify.
        """
        if not self._has_hmp_command(cmd):
            raise MonitorNotSupportedCmdError(self.name, cmd)

    def _log_response(self, cmd, resp, debug=True):
        """
        Print log message for monitor cmd's response.

        :param cmd: Command string.
        :param resp: Response from monitor command.
        :param debug: Whether to print the commands.
        """
        def _log_output(o, indent=0):
            logging.debug("(monitor %s)    %s%s",
                          self.name, " " * indent, o)

        def _dump_list(li, indent=0):
            for l in li:
                if isinstance(l, dict):
                    _dump_dict(l, indent + 2)
                else:
                    _log_output(str(l), indent)

        def _dump_dict(di, indent=0):
            for k, v in di.iteritems():
                o = "%s%s: " % (" " * indent, k)
                if isinstance(v, dict):
                    _log_output(o, indent)
                    _dump_dict(v, indent + 2)
                elif isinstance(v, list):
                    _log_output(o, indent)
                    _dump_list(v, indent + 2)
                else:
                    o += str(v)
                    _log_output(o, indent)

        if self.debug_log or debug:
            logging.debug("(monitor %s) Response to '%s' "
                          "(re-formated)", self.name, cmd)
            if isinstance(resp, dict):
                _dump_dict(resp)
            elif isinstance(resp, list):
                _dump_list(resp)
            else:
                for l in str(resp).splitlines():
                    _log_output(l)

    # Public methods
    def cmd(self, cmd, args=None, timeout=CMD_TIMEOUT, debug=True, fd=None):
        """
        Send a QMP monitor command and return the response.

        Note: an id is automatically assigned to the command and the response
        is checked for the presence of the same id.

        :param cmd: Command to send
        :param args: A dict containing command arguments, or None
        :param timeout: Time duration to wait for response
        :param debug: Whether to print the commands being sent and responses
        :param fd: file object or file descriptor to pass

        :return: The response received

        :raise MonitorLockError: Raised if the lock cannot be acquired
        :raise MonitorSocketError: Raised if a socket error occurs
        :raise MonitorProtocolError: Raised if no response is received
        :raise QMPCmdError: Raised if the response is an error message
                            (the exception's args are (cmd, args, data)
                            where data is the error data)
        """
        self._log_command(cmd, debug)
        if not self._acquire_lock():
            raise MonitorLockError("Could not acquire exclusive lock to send "
                                   "QMP command '%s'" % cmd)

        try:
            # Read any data that might be available
            self._read_objects()
            # Send command
            q_id = utils_misc.generate_random_string(8)
            cmdobj = self._build_cmd(cmd, args, q_id)
            if debug:
                logging.debug("Send command: %s" % cmdobj)
            if fd is not None:
                if self._passfd is None:
                    self._passfd = passfd_setup.import_passfd()
                # If command includes a file descriptor, use passfd module
                self._passfd.sendfd(
                    self._socket, fd, json.dumps(cmdobj) + "\n")
            else:
                self._send(json.dumps(cmdobj) + "\n")
            # Read response
            r = self._get_response(q_id, timeout)
            if r is None:
                raise MonitorProtocolError("Received no response to QMP "
                                           "command '%s', or received a "
                                           "response with an incorrect id"
                                           % cmd)
            if "return" in r:
                ret = r["return"]
                if ret:
                    self._log_response(cmd, ret, debug)
                return ret
            if "error" in r:
                raise QMPCmdError(cmd, args, r["error"])

        finally:
            self._lock.release()

    def cmd_raw(self, data, timeout=CMD_TIMEOUT):
        """
        Send a raw string to the QMP monitor and return the response.
        Unlike cmd(), return the raw response dict without performing any
        checks on it.

        :param data: The data to send
        :param timeout: Time duration to wait for response
        :return: The response received
        :raise MonitorLockError: Raised if the lock cannot be acquired
        :raise MonitorSocketError: Raised if a socket error occurs
        :raise MonitorProtocolError: Raised if no response is received
        """
        if not self._acquire_lock():
            raise MonitorLockError("Could not acquire exclusive lock to send "
                                   "data: %r" % data)

        try:
            self._read_objects()
            self._send(data)
            r = self._get_response(None, timeout)
            if r is None:
                raise MonitorProtocolError("Received no response to data: %r" %
                                           data)
            return r

        finally:
            self._lock.release()

    def cmd_obj(self, obj, timeout=CMD_TIMEOUT):
        """
        Transform a Python object to JSON, send the resulting string to the QMP
        monitor, and return the response.
        Unlike cmd(), return the raw response dict without performing any
        checks on it.

        :param obj: The object to send
        :param timeout: Time duration to wait for response
        :return: The response received
        :raise MonitorLockError: Raised if the lock cannot be acquired
        :raise MonitorSocketError: Raised if a socket error occurs
        :raise MonitorProtocolError: Raised if no response is received
        """
        return self.cmd_raw(json.dumps(obj) + "\n", timeout)

    def cmd_qmp(self, cmd, args=None, q_id=None, timeout=CMD_TIMEOUT):
        """
        Build a QMP command from the passed arguments, send it to the monitor
        and return the response.
        Unlike cmd(), return the raw response dict without performing any
        checks on it.

        :param cmd: Command to send
        :param args: A dict containing command arguments, or None
        :param id:  An id for the command, or None
        :param timeout: Time duration to wait for response
        :return: The response received
        :raise MonitorLockError: Raised if the lock cannot be acquired
        :raise MonitorSocketError: Raised if a socket error occurs
        :raise MonitorProtocolError: Raised if no response is received
        """
        return self.cmd_obj(self._build_cmd(cmd, args, q_id), timeout)

    def verify_responsive(self):
        """
        Make sure the monitor is responsive by sending a command.
        """
        self.cmd(cmd="query-status", debug=False)

    def get_status(self):
        """
        Get VM status.

        :return: return VM status
        """
        return self.cmd(cmd="query-status", debug=False)

    def verify_status(self, status):
        """
        Verify VM status

        :param status: Optional VM status, 'running' or 'paused'
        :return: return True if VM status is same as we expected
        """
        o = dict(self.cmd(cmd="query-status", debug=False))
        if status == 'paused':
            return (o['running'] is False)
        if status == 'running':
            return (o['running'] is True)
        if o['status'] == status:
            return True
        return False

    def get_events(self):
        """
        Return a list of the asynchronous events received since the last
        clear_events() call.

        :return: A list of events (the objects returned have an "event" key)
        :raise MonitorLockError: Raised if the lock cannot be acquired
        """
        if not self._acquire_lock():
            raise MonitorLockError("Could not acquire exclusive lock to read "
                                   "QMP events")
        try:
            self._read_objects()
            return self._events[:]
        finally:
            self._lock.release()

    def get_event(self, name):
        """
        Look for an event with the given name in the list of events.

        :param name: The name of the event to look for (e.g. 'RESET')
        :return: An event object or None if none is found
        """
        for e in self.get_events():
            if e.get("event") == name:
                return e

    def human_monitor_cmd(self, cmd="", timeout=CMD_TIMEOUT,
                          debug=True, fd=None):
        """
        Run human monitor command in QMP through human-monitor-command

        :param cmd: human monitor command.
        :param timeout: Time duration to wait for response
        :param debug: Whether to print the commands being sent and responses
        :param fd: file object or file descriptor to pass

        :return: The response to the command
        """
        self._log_command(cmd, extra_str="(via Human Monitor)")

        args = {"command-line": cmd}
        ret = self.cmd("human-monitor-command", args, timeout, False, fd)

        if ret:
            self._log_response(cmd, ret, debug)
        return ret

    def clear_events(self):
        """
        Clear the list of asynchronous events.

        :raise MonitorLockError: Raised if the lock cannot be acquired
        """
        if not self._acquire_lock():
            raise MonitorLockError("Could not acquire exclusive lock to clear "
                                   "QMP event list")
        self._events = []
        self._lock.release()

    def clear_event(self, name):
        """
        Clear a kinds of events in events list only.

        :raise MonitorLockError: Raised if the lock cannot be acquired
        """
        if not self._acquire_lock():
            raise MonitorLockError("Could not acquire exclusive lock to clear "
                                   "QMP event list")
        while True:
            event = self.get_event(name)
            if event:
                self._events.remove(event)
            else:
                break
        self._lock.release()

    def get_greeting(self):
        """
        Return QMP greeting message.
        """
        return self._greeting

    # Command wrappers
    # Note: all of the following functions raise exceptions in a similar manner
    # to cmd().
    def send_args_cmd(self, cmdlines, timeout=CMD_TIMEOUT, convert=True):
        """
        Send a command with/without parameters and return its output.
        Have same effect with cmd function.
        Implemented under the same name for both the human and QMP monitors.
        Command with parameters should in following format e.g.:
        'memsave val=0 size=10240 filename=memsave'
        Command without parameter: 'query-vnc'

        :param cmdlines: Commands send to qemu which is separated by ";". For
                         command with parameters command should send in a string
                         with this format:
                         $command $arg_name=$arg_value $arg_name=$arg_value
        :param timeout: Time duration to wait for (qemu) prompt after command
        :param convert: If command need to convert. For commands not in standard
                        format such as: $command $arg_value
        :return: The response to the command
        :raise MonitorLockError: Raised if the lock cannot be acquired
        :raise MonitorSendError: Raised if the command cannot be sent
        :raise MonitorProtocolError: Raised if no response is received
        """
        cmd_output = []
        for cmdline in cmdlines.split(";"):
            command = cmdline.split()[0]
            if not self._has_command(command):
                if "=" in cmdline:
                    command = cmdline.split()[0]
                    self.verify_supported_hmp_cmd(command)

                    cmdargs = " ".join(cmdline.split()[1:]).split(",")
                    for arg in cmdargs:
                        value = "=".join(arg.split("=")[1:])
                        if arg.split("=")[0] == "cert-subject":
                            value = value.replace('/', ',')

                        command += " " + value
                else:
                    command = cmdline
                cmd_output.append(self.human_monitor_cmd(command))
            else:
                cmdargs = " ".join(cmdline.split()[1:]).split(",")
                args = {}
                for arg in cmdargs:
                    opt = arg.split('=')
                    value = "=".join(opt[1:])
                    try:
                        if re.match("^[0-9]+$", value):
                            value = int(value)
                        elif re.match("^[0-9]+\.[0-9]*$", value):
                            value = float(value)
                        elif re.findall("true", value, re.I):
                            value = True
                        elif re.findall("false", value, re.I):
                            value = False
                        else:
                            value = value.strip()
                        if opt[0] == "cert-subject":
                            value = value.replace('/', ',')
                        if opt[0]:
                            args[opt[0].strip()] = value
                    except:
                        logging.debug("Fail to create args, please check cmd")
                cmd_output.append(self.cmd(command, args, timeout=timeout))
        if len(cmd_output) == 1:
            return cmd_output[0]
        return cmd_output

    def quit(self):
        """
        Send "quit" and return the response.
        """
        return self.cmd("quit")

    def info(self, what, debug=True):
        """
        Request info about something and return the response.
        """
        cmd = "query-%s" % what
        if not self._has_command(cmd):
            cmd = "info %s" % what
            return self.human_monitor_cmd(cmd, debug=debug)

        return self.cmd(cmd, debug=debug)

    def query(self, what, debug=True):
        """
        Alias for info.
        """
        return self.info(what, debug)

    def screendump(self, filename, debug=True):
        """
        Request a screendump.

        :param filename: Location for the screendump
        :param debug: Whether to print the commands being sent and responses

        :return: The response to the command
        """
        cmd = "screendump"
        if not self._has_command(cmd):
            self.verify_supported_hmp_cmd(cmd)
            cmdline = "%s %s" % (cmd, filename)
            return self.human_monitor_cmd(cmdline, debug=debug)

        args = {"filename": filename}
        return self.cmd(cmd=cmd, args=args, debug=debug)

    def sendkey(self, keystr, hold_time=1):
        """
        Send key combination to VM.

        :param keystr: Key combination string
        :param hold_time: Hold time in ms (should normally stay 1 ms)

        :return: The response to the command
        """
        return self.human_monitor_cmd("sendkey %s %s" % (keystr, hold_time))

    def migrate(self, uri, full_copy=False, incremental_copy=False, wait=False):
        """
        Migrate.

        :param uri: destination URI
        :param full_copy: If true, migrate with full disk copy
        :param incremental_copy: If true, migrate with incremental disk copy
        :param wait: If true, wait for completion
        :return: The response to the command
        """
        args = {"uri": uri,
                "blk": full_copy,
                "inc": incremental_copy}
        args['uri'] = re.sub('"', "", args['uri'])
        try:
            return self.cmd("migrate", args)
        except QMPCmdError, e:
            if e.data['class'] in ['SockConnectInprogress', 'GenericError']:
                logging.debug(
                    "Migrate socket connection still initializing...")
            else:
                raise e

    def migrate_set_speed(self, value):
        """
        Set maximum speed (in bytes/sec) for migrations.

        :param value: Speed in bytes/sec
        :return: The response to the command
        """
        value = utils.convert_data_size(value, "M")
        args = {"value": value}
        return self.cmd("migrate_set_speed", args)

    def set_link(self, name, up):
        """
        Set link up/down.

        :param name: Link name
        :param up: Bool value, True=set up this link, False=Set down this link

        :return: The response to the command
        """
        return self.send_args_cmd("set_link name=%s,up=%s" % (name, str(up)))

    def migrate_set_downtime(self, value):
        """
        Set maximum tolerated downtime (in seconds) for migration.

        :param value: maximum downtime (in seconds)

        :return: The command's output
        """
        val = value * 10 ** 9
        args = {"value": val}
        return self.cmd("migrate_set_downtime", args)

    def live_snapshot(self, device, snapshot_file, snapshot_format="qcow2"):
        """
        Take a live disk snapshot.

        :param device: device id of base image
        :param snapshot_file: image file name of snapshot
        :param snapshot_format: image format of snapshot

        :return: The response to the command
        """
        args = {"device": device,
                "snapshot-file": snapshot_file,
                "format": snapshot_format}
        return self.cmd("blockdev-snapshot-sync", args)

    def block_stream(self, device, speed=None, base=None,
                     cmd="block-stream", correct=True):
        """
        Start block-stream job;

        :param device: device ID
        :param speed: int type, limited speed(B/s)
        :param base: base file
        :param correct: auto correct command, correct by default

        :return: The command's output
        """
        if correct:
            cmd = self.correct(cmd)
        self.verify_supported_cmd(cmd)
        args = {"device": device}
        if speed is not None:
            args["speed"] = speed
        if base:
            args["base"] = base
        return self.cmd(cmd, args)

    def set_block_job_speed(self, device, speed=0,
                            cmd="block-job-set-speed", correct=True):
        """
        Set limited speed for runnig job on the device

        :param device: device ID
        :param speed: int type, limited speed(B/s)
        :param correct: auto correct command, correct by default

        :return: The command's output
        """
        if correct:
            cmd = self.correct(cmd)
        self.verify_supported_cmd(cmd)
        args = {"device": device,
                "speed": speed}
        return self.cmd(cmd, args)

    def cancel_block_job(self, device, cmd="block-job-cancel", correct=True):
        """
        Cancel running block stream/mirror job on the device

        :param device: device ID
        :param correct: auto correct command, correct by default

        :return: The command's output
        """
        if correct:
            cmd = self.correct(cmd)
        self.verify_supported_cmd(cmd)
        args = {"device": device}
        return self.cmd(cmd, args)

    def query_block_job(self, device):
        """
        Get block job status on the device

        :param device: device ID

        :return: dict about job info, return empty dict if no active job
        """
        job = dict()
        output = str(self.info("block-jobs"))
        try:
            job = filter(lambda x: x.get("device") == device,
                         eval(output))[0]
        except Exception:
            pass
        return job

    def get_backingfile(self, device):
        """
        Return "backing_file" path of the device

        :param device: device ID

        :return: string, backing_file path
        """
        backing_file = None
        block_info = self.query("block")
        try:
            image_info = filter(lambda x: x["device"] == device, block_info)[0]
            backing_file = image_info["inserted"].get("backing_file")
        except Exception:
            pass
        return backing_file

    def block_mirror(self, device, target, speed, sync, format, mode,
                     cmd="drive-mirror", correct=True):
        """
        Start mirror type block device copy job

        :param device: device ID
        :param target: target image
        :param speed: limited speed, unit is B/s
        :param sync: what parts of the disk image should be copied to the
                     destination;
        :param mode: 'absolute-paths' or 'existing'
        :param format: target image format
        :param cmd: block mirror command
        :param correct: auto correct command, correct by default

        :return: The command's output
        """
        if correct:
            cmd = self.correct(cmd)
        self.verify_supported_cmd(cmd)
        args = {"device": device,
                "target": target}
        if cmd.startswith("__com.redhat"):
            args["full"] = sync
        else:
            args["sync"] = sync
        if mode:
            args["mode"] = mode
        if format:
            args["format"] = format
        if speed:
            args["speed"] = speed
        return self.cmd(cmd, args)

    def block_reopen(self, device, new_image_file, image_format,
                     cmd="block-job-complete", correct=True):
        """
        Reopen new target image;

        :param device: device ID
        :param new_image_file: new image file name
        :param image_format: new image file format
        :param cmd: image reopen command
        :param correct: auto correct command, correct by default

        :return: the command's output
        """
        if correct:
            cmd = self.correct(cmd)
        self.verify_supported_cmd(cmd)
        args = {"device": device}
        if cmd.startswith("__"):
            args["new-image-file"] = new_image_file
            args["format"] = image_format
        return self.cmd(cmd, args)

    def getfd(self, fd, name):
        """
        Receives a file descriptor

        :param fd: File descriptor to pass to QEMU
        :param name: File descriptor name (internal to QEMU)

        :return: The response to the command
        """
        args = {"fdname": name}
        return self.cmd("getfd", args, fd=fd)

    def system_wakeup(self):
        """
        Wakeup suspended guest.
        """
        cmd = "system_wakeup"
        self.verify_supported_cmd(cmd)
        return self.cmd(cmd)

    def nmi(self):
        """
        Inject a NMI on all guest's CPUs.
        """
        return self.cmd("inject-nmi")

    def block_resize(self, device, size):
        """
        Resize the block device size

        :param device: Block device name
        :param size: Block device size need to set to. Unit is bytes.
        :return: Command output
        """
        cmd = "block_resize device=%s,size=%s" % (device, size)
        return self.send_args_cmd(cmd)

    def eject_cdrom(self, device, force=False):
        """
        Eject media of cdrom and open cdrom door;
        """
        cmd = "eject"
        self.verify_supported_cmd(cmd)
        args = {"device": device, "force": force}
        return self.cmd(cmd, args)

    def change_media(self, device, target):
        """
        Change media of cdrom of drive;
        """
        cmd = "change"
        self.verify_supported_cmd(cmd)
        args = {"device": device, "target": target}
        return self.cmd(cmd, args)
