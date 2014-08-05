"""
Interfaces and helpers for the virtio_serial ports.

:copyright: 2012 Red Hat Inc.
"""
from threading import Thread
from collections import deque
import aexpect
import logging
import os
import random
import select
import socket
import time
from autotest.client.shared import error, utils
import utils_test
import data_dir


SOCKET_SIZE = 2048


class VirtioPortException(Exception):

    """ General virtio_port exception """
    pass


class VirtioPortFatalException(VirtioPortException):

    """ Fatal virtio_port exception """
    pass


class _VirtioPort(object):

    """
    Define structure to keep information about used port.
    """

    def __init__(self, qemu_id, name, hostfile):
        """
        :param name: Name of port for guest side.
        :param hostfile: Path to port on host side.
        """
        self.qemu_id = qemu_id
        self.name = name
        self.hostfile = hostfile
        self.is_console = None  # "yes", "no"
        self.sock = None
        self.port_was_opened = None

    def __str__(self):
        """
        Convert to text.
        """
        return ("%s,%s,%s,%s,%d" % ("Socket", self.name, self.is_console,
                                    self.hostfile, self.is_open()))

    def __getstate__(self):
        """
        socket is unpickable so we need to remove it and say it's closed.
        Used by autotest env.
        """
        # TODO: add port cleanup into qemu_vm.py
        if self.is_open():
            logging.warn("Force closing virtio_port socket, FIX the code to "
                         " close the socket prior this to avoid possible err.")
            self.close()
        return self.__dict__.copy()

    def is_open(self):
        """ :return: host port status (open/closed) """
        if self.sock:
            return True
        else:
            return False

    def for_guest(self):
        """
        Format data for communication with guest side.
        """
        return [self.name, self.is_console]

    def open(self):     # @ReservedAssignment
        """
        Open port on host side.
        """
        if self.is_open():
            return
        attempt = 11
        while attempt > 0:
            try:
                self.sock = socket.socket(socket.AF_UNIX,
                                          socket.SOCK_STREAM)
                self.sock.settimeout(1)
                self.sock.connect(self.hostfile)
                self.sock.setsockopt(1, socket.SO_SNDBUF, SOCKET_SIZE)
                self.sock.settimeout(None)
                self.port_was_opened = True
                return
            except Exception:
                attempt -= 1
                time.sleep(1)
        raise error.TestFail("Can't open the %s sock (%s)" % (self.name,
                                                              self.hostfile))

    def clean_port(self):
        """
        Clean all data from opened port on host side.
        """
        if self.is_open():
            self.close()
        elif not self.port_was_opened:
            # BUG: Don't even try opening port which was never used. It
            # hangs for ever... (virtio_console bug)
            logging.debug("No need to clean port %s", self)
            return
        logging.debug("Cleaning port %s", self)
        self.open()
        ret = select.select([self.sock], [], [], 1.0)
        if ret[0]:
            buf = self.sock.recv(1024)
            logging.debug("Rest in socket: " + buf)

    def close(self):
        """
        Close port.
        """
        if self.is_open():
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
            self.sock = None

    def mark_as_clean(self):
        """
        Mark port as cleaned
        """
        self.port_was_opened = False


class VirtioSerial(_VirtioPort):

    """ Class for handling virtio-serialport """

    def __init__(self, qemu_id, name, hostfile):
        """
        :param name: Name of port for guest side.
        :param hostfile: Path to port on host side.
        """
        super(VirtioSerial, self).__init__(qemu_id, name, hostfile)
        self.is_console = "no"


class VirtioConsole(_VirtioPort):

    """ Class for handling virtio-console """

    def __init__(self, qemu_id, name, hostfile):
        """
        :param name: Name of port for guest side.
        :param hostfile: Path to port on host side.
        """
        super(VirtioConsole, self).__init__(qemu_id, name, hostfile)
        self.is_console = "yes"


class GuestWorker(object):

    """
    Class for executing "virtio_console_guest" script on guest
    """

    def __init__(self, vm):
        """ Initialize worker for use (including port init on guest) """
        self.vm = vm
        self.session = self.vm.wait_for_login()
        self.__cmd_execute_worker = None

        # Detect the OS version
        guest_script_py = "virtio_console_guest.py"
        out = self.session.cmd_output("echo on")
        if "on" in out:
            self.os_linux = True
            guest_script_path = "/tmp/%s" % guest_script_py
            cmd_guest_size = ("du -b %s | cut -f1"
                              % guest_script_path)
            cmd_already_compiled_chck = "ls %so" % guest_script_path
            cmd_compile = ("python -OO %s -c "
                           "&& echo -n 'PASS: Compile virtio_guest finished' "
                           "|| echo -n 'FAIL: Compile virtio_guest failed'"
                           % guest_script_path)
            self.__cmd_execute_worker = ("python %so"
                                         "&& echo -n 'PASS: virtio_guest finished' "
                                         "|| echo -n 'FAIL: virtio_guest failed'"
                                         % guest_script_path)
        else:
            self.os_linux = False
            guest_script_path = "C:\\%s" % guest_script_py
            cmd_guest_size = ("for %%I in (%s) do @echo %%~zI"
                              % guest_script_path)
            cmd_already_compiled_chck = "dir %so" % guest_script_path
            cmd_compile = ("%s -c "
                           "&& echo PASS: Compile virtio_guest finished "
                           "|| echo FAIL: Compile virtio_guest failed"
                           % guest_script_path)
            self.__cmd_execute_worker = ("%so "
                                         "&& echo PASS: virtio_guest finished "
                                         "|| echo FAIL: virtio_guest failed"
                                         % guest_script_path)

        # Copy, compile and run the worker
        timeout = 10
        base_path = os.path.dirname(data_dir.get_data_dir())
        guest_script_src = os.path.join(base_path, 'scripts',
                                        'virtio_console_guest.py')
        script_size = utils.system_output("du -b %s | cut -f1"
                                          % guest_script_src).strip()
        script_size_guest = self.session.cmd_output(cmd_guest_size).strip()
        if (script_size != script_size_guest
                or self.session.cmd_status(cmd_already_compiled_chck)):
            if self.os_linux:
                # Disable serial-getty@hvc0.service on systemd-like hosts
                self.session.cmd_status('systemctl mask '
                                        'serial-getty@hvc0.service')
                self.session.cmd_status('systemctl stop '
                                        'serial-getty@hvc0.service')
            # Copy virtio_console_guest.py into guests
            self.vm.copy_files_to(guest_script_src, guest_script_path)

            # set echo off (self.cmd() musn't contain C:)
            self.session.sendline("echo off")
            # Compile worker
            logging.debug("Compile %s on guest %s", guest_script_py,
                          self.vm.name)
            try:
                self.cmd(cmd_compile, timeout)
            except VirtioPortException:
                if not self.os_linux:
                    logging.error("Script execution failed, do you have python"
                                  " and pywin32 installed? Currently this "
                                  "needs to be done manually!")
                raise
            self.session.sendline()

        # set echo off (self.cmd() musn't contain C:)
        self.session.sendline("echo off")
        logging.debug("Starting %so on guest %s", guest_script_py,
                      self.vm.name)
        self._execute_worker(timeout)
        self._init_guest(timeout)

    def _execute_worker(self, timeout=10):
        """ Execute worker on guest """
        try:
            self.cmd(self.__cmd_execute_worker, timeout)
        except VirtioPortException:
            if not self.os_linux:
                logging.error("Script execution failed, do you have python"
                              " and pywin32 installed? Currently this "
                              "needs to be done manually!")
            raise
        # Let the system rest
        # FIXME: Is this always necessarily?
        time.sleep(2)

    def _init_guest(self, timeout=10):
        """ Initialize worker on guest """
        ports = []
        for port in self.vm.virtio_ports:
            ports.append(port.for_guest())
        self.cmd("virt.init(%s)" % (ports), timeout)

    def reconnect(self, vm, timeout=10):
        """
        Reconnect to guest_worker (eg. after migration)
        :param vm: New VM object
        """
        self.vm = vm
        self.session = self.vm.wait_for_login()
        self._execute_worker(timeout)

    def cmd(self, cmd, timeout=10, patterns=None):
        """
        Wrapper around the self.cmd command which executes the command on
        guest. Unlike self._cmd command when the command fails it raises the
        test error.
        :param command: Command that will be executed.
        :param timeout: Timeout used to verify expected output.
        :return: Tuple (match index, data)
        """
        match, data = self._cmd(cmd, timeout, patterns)
        if match == 1 or match is None:
            raise VirtioPortException("Failed to execute '%s' on"
                                      " virtio_console_guest.py, "
                                      "vm: %s, output:\n%s" %
                                      (cmd, self.vm.name, data))
        return (match, data)

    def _cmd(self, cmd, timeout=10, patterns=None):
        """
        Execute given command inside the script's main loop.
        :param command: Command that will be executed.
        :param timeout: Timeout used to verify expected output.
        :param patterns: Expected patterns; have to startwith ^PASS: or ^FAIL:
        :return: Tuple (match index, data)
        """
        if not patterns:
            patterns = ("^PASS:", "^FAIL:")
        logging.debug("Executing '%s' on virtio_console_guest.py,"
                      " vm: %s, timeout: %s", cmd, self.vm.name, timeout)
        self.session.sendline(cmd)
        try:
            (match, data) = self.session.read_until_any_line_matches(patterns,
                                                                     timeout=timeout)
            if patterns[match].startswith('^PASS:'):
                match = 0
            elif patterns[match].startswith('^FAIL:'):
                match = 1
            else:
                data = ("Incorrect pattern %s. Data in console:\n%s"
                        % (patterns[match], data))
                match = None
        except aexpect.ExpectError, inst:
            match = None
            data = "Cmd process timeout. Data in console:\n" + inst.output

        self.vm.verify_kernel_crash()

        return (match, data)

    def read_nonblocking(self, internal_timeout=None, timeout=None):
        """
        Reads-out all remaining output from GuestWorker.

        :param internal_timeout: Time (seconds) to wait before we give up
                                 reading from the child process, or None to
                                 use the default value.
        :param timeout: Timeout for reading child process output.
        """
        return self.session.read_nonblocking(internal_timeout, timeout)

    def _cleanup_ports(self):
        """
        Read all data from all ports, in both sides of each port.
        """
        for port in self.vm.virtio_ports:
            openned = port.is_open()
            port.clean_port()
            self.cmd("virt.clean_port('%s'),1024" % port.name, 10)
            if not openned:
                port.close()
                self.cmd("virt.close('%s'),1024" % port.name, 10)

    def safe_exit_loopback_threads(self, send_pts, recv_pts):
        """
        Safely executes on_guest("virt.exit_threads()") using workaround of
        the stuck thread in loopback in mode=virt.LOOP_NONE .
        :param send_pts: list of possible send sockets we need to work around.
        :param recv_pts: list of possible recv sockets we need to read-out.
        """
        # No need to clean ports when VM is dead
        if not self.vm or self.vm.is_dead():
            return
        # in LOOP_NONE mode it might stuck in read/write
        # This command can't fail, can only freze so wait for the correct msg
        match, tmp = self._cmd("virt.exit_threads()", 3, ("^PASS: All threads"
                                                          " finished",))
        if match is None:
            logging.warn("Workaround the stuck thread on guest")
            # Thread is stuck in read/write
            for send_pt in send_pts:
                send_pt.sock.sendall(".")
        elif match != 0:
            # Something else
            raise VirtioPortException("Unexpected fail\nMatch: %s\nData:\n%s"
                                      % (match, tmp))

        # Read-out all remaining data
        for recv_pt in recv_pts:
            while select.select([recv_pt.sock], [], [], 0.1)[0]:
                recv_pt.sock.recv(1024)

        # This will cause fail in case anything went wrong.
        match, tmp = self._cmd("print 'PASS: nothing'", 10, ('^PASS: nothing',
                                                             '^FAIL:'))
        if match is not 0:
            logging.error("Python is stuck/FAILed after read-out:\n%s", tmp)
            try:
                self.session.close()
                self.session = self.vm.wait_for_login()
                if self.os_linux:   # On windows it dies with the connection
                    self.cmd("killall -9 python "
                             "&& echo -n PASS: python killed"
                             "|| echo -n PASS: python was already dead", 10)
                self._execute_worker()
                self._init_guest()
            except Exception, inst:
                logging.error(inst)
                raise VirtioPortFatalException("virtio-console driver is "
                                               "irreparably blocked, further tests might FAIL.")

    def cleanup_ports(self):
        """
        Clean state of all ports and set port to default state.

        Default state: No data on port or in port buffer. Read mode = blocking.
        """
        # Check if python is still alive
        match, tmp = self._cmd("is_alive()", 10)
        if match is not 0:
            logging.error("Python died/is stuck/have remaining threads")
            logging.debug(tmp)
            try:
                self.vm.verify_kernel_crash()

                match, tmp = self._cmd("guest_exit()", 10, ('^FAIL:',
                                                            '^PASS: virtio_guest finished'))
                self.session.close()
                self.session = self.vm.wait_for_login()
                # On windows it dies with the connection
                if match is not 0 and self.os_linux:
                    logging.debug(tmp)
                    self.cmd("killall -9 python "
                             "&& echo -n PASS: python killed"
                             "|| echo -n PASS: python was already dead", 10)

                self._execute_worker()
                self._init_guest()
                self._cleanup_ports()

            except Exception, inst:
                logging.error(inst)
                raise VirtioPortFatalException("virtio-console driver is "
                                               "irreparably blocked, further tests might FAIL.")

    def cleanup(self):
        """ Cleanup ports and quit the worker """
        # Verify that guest works
        if self.session and self.vm and self.vm.is_alive():
            self.cleanup_ports()
        if self.vm:
            self.vm.verify_kernel_crash()
        # Quit worker
        if self.session and self.vm and self.vm.is_alive():
            match, tmp = self._cmd("guest_exit()", 10)
            self.session.close()
            # On windows it dies with the connection
            if match is not 0 and self.os_linux:
                logging.warn('guest_worker stuck during cleanup:\n%s\n,'
                             ' killing python...', tmp)
                self.session = self.vm.wait_for_login()
                self.cmd("killall -9 python "
                         "&& echo -n PASS: python killed"
                         "|| echo -n PASS: python was already dead", 10)
                self.session.close()
        self.session = None
        self.vm = None


class ThSend(Thread):

    """
    Random data sender thread.
    """

    def __init__(self, port, data, exit_event, quiet=False):
        """
        :param port: Destination port.
        :param data: The data intend to be send in a loop.
        :param exit_event: Exit event.
        :param quiet: If true don't raise event when crash.
        """
        Thread.__init__(self)
        self.port = port
        # FIXME: socket.send(data>>127998) without read blocks thread
        if len(data) > 102400:
            data = data[0:102400]
            logging.error("Data is too long, using only first %d bytes",
                          len(data))
        self.data = data
        self.exitevent = exit_event
        self.idx = 0
        self.quiet = quiet
        self.ret_code = 1    # sets to 0 when finish properly

    def run(self):
        logging.debug("ThSend %s: run", self.getName())
        try:
            while not self.exitevent.isSet():
                self.idx += self.port.send(self.data)
            logging.debug("ThSend %s: exit(%d)", self.getName(),
                          self.idx)
        except Exception, ints:
            if not self.quiet:
                raise ints
            logging.debug(ints)
        self.ret_code = 0


class ThSendCheck(Thread):

    """
    Random data sender thread.
    """

    def __init__(self, port, exit_event, queues, blocklen=1024,
                 migrate_event=None, reduced_set=False):
        """
        :param port: Destination port
        :param exit_event: Exit event
        :param queues: Queues for the control data (FIFOs)
        :param blocklen: Block length
        :param migrate_event: Event indicating port was changed and is ready.
        """
        Thread.__init__(self)
        self.port = port
        self.queues = queues
        # FIXME: socket.send(data>>127998) without read blocks thread
        if blocklen > 102400:
            blocklen = 102400
            logging.error("Data is too long, using blocklen = %d",
                          blocklen)
        self.blocklen = blocklen
        self.exitevent = exit_event
        self.migrate_event = migrate_event
        self.idx = 0
        self.ret_code = 1    # sets to 0 when finish properly
        self.reduced_set = reduced_set

    def run(self):
        logging.debug("ThSendCheck %s: run", self.getName())
        _err_msg_exception = ('ThSendCheck ' + str(self.getName()) + ': Got '
                              'exception %s, continuing')
        _err_msg_disconnect = ('ThSendCheck ' + str(self.getName()) + ': Port '
                               'disconnected, waiting for new port.')
        _err_msg_reconnect = ('ThSendCheck ' + str(self.getName()) + ': Port '
                              'reconnected, continuing.')
        too_much_data = False
        if self.reduced_set:
            rand_a = 65
            rand_b = 91
        else:
            rand_a = 0
            rand_b = 255
        while not self.exitevent.isSet():
            # FIXME: workaround the problem with qemu-kvm stall when too
            # much data is sent without receiving
            for queue in self.queues:
                while not self.exitevent.isSet() and len(queue) > 1048576:
                    too_much_data = True
                    time.sleep(0.1)
            try:
                ret = select.select([], [self.port.sock], [], 1.0)
            except Exception, inst:
                # self.port is not yet set while reconnecting
                if self.migrate_event is None:
                    raise error.TestFail("ThSendCheck %s: Broken pipe. If this"
                                         " is expected behavior set migrate_event "
                                         "to support reconnection." % self.getName())
                if self.port.sock is None:
                    logging.debug(_err_msg_disconnect)
                    while self.port.sock is None:
                        if self.exitevent.isSet():
                            break
                        time.sleep(0.1)
                    logging.debug(_err_msg_reconnect)
                else:
                    logging.debug(_err_msg_exception, inst)
                continue
            if ret[1]:
                # Generate blocklen of random data add them to the FIFO
                # and send them over virtio_console
                buf = ""
                for _ in range(self.blocklen):
                    char = "%c" % random.randrange(rand_a, rand_b)
                    buf += char
                    for queue in self.queues:
                        queue.append(char)
                target = self.idx + self.blocklen
                while not self.exitevent.isSet() and self.idx < target:
                    try:
                        idx = self.port.sock.send(buf)
                    except Exception, inst:
                        # Broken pipe
                        if not hasattr(inst, 'errno') or inst.errno != 32:
                            continue
                        if self.migrate_event is None:
                            self.exitevent.set()
                            raise error.TestFail("ThSendCheck %s: Broken "
                                                 "pipe. If this is expected behavior "
                                                 "set migrate_event to support "
                                                 "reconnection." % self.getName())
                        logging.debug("ThSendCheck %s: Broken pipe "
                                      ", reconnecting. ", self.getName())
                        attempt = 10
                        while (attempt > 1
                               and not self.exitevent.isSet()):
                            # Wait until main thread sets the new self.port
                            while not (self.exitevent.isSet()
                                       or self.migrate_event.wait(1)):
                                pass
                            if self.exitevent.isSet():
                                break
                            logging.debug("ThSendCheck %s: Broken pipe resumed"
                                          ", reconnecting...", self.getName())
                            self.port.sock = False
                            self.port.open()
                            try:
                                idx = self.port.sock.send(buf)
                            except Exception:
                                attempt -= 1
                                time.sleep(10)
                            else:
                                attempt = 0
                    buf = buf[idx:]
                    self.idx += idx
        logging.debug("ThSendCheck %s: exit(%d)", self.getName(),
                      self.idx)
        if too_much_data:
            logging.error("ThSendCheck: working around the 'too_much_data'"
                          "bug")
        self.ret_code = 0


class ThRecv(Thread):

    """
    Receives data and throws it away.
    """

    def __init__(self, port, event, blocklen=1024, quiet=False):
        """
        :param port: Data source port.
        :param event: Exit event.
        :param blocklen: Block length.
        :param quiet: If true don't raise event when crash.
        """
        Thread.__init__(self)
        self.port = port
        self._port_timeout = self.port.gettimeout()
        self.port.settimeout(0.1)
        self.exitevent = event
        self.blocklen = blocklen
        self.idx = 0
        self.quiet = quiet
        self.ret_code = 1    # sets to 0 when finish properly

    def run(self):
        logging.debug("ThRecv %s: run", self.getName())
        try:
            while not self.exitevent.isSet():
                # TODO: Workaround, it didn't work with select :-/
                try:
                    self.idx += len(self.port.recv(self.blocklen))
                except socket.timeout:
                    pass
            self.port.settimeout(self._port_timeout)
            logging.debug("ThRecv %s: exit(%d)", self.getName(), self.idx)
        except Exception, ints:
            if not self.quiet:
                raise ints
            logging.debug(ints)
        self.ret_code = 0


class ThRecvCheck(Thread):

    """
    Random data receiver/checker thread.
    """

    def __init__(self, port, buff, exit_event, blocklen=1024, sendlen=0,
                 migrate_event=None, debug=None):
        """
        :param port: Source port.
        :param buff: Control data buffer (FIFO).
        :param exit_event: Exit event.
        :param blocklen: Block length.
        :param sendlen: Block length of the send function (on guest)
        :param migrate_event: Event indicating port was changed and is ready.
        :param debug: Set the execution mode, when nothing run normal.
        """
        Thread.__init__(self)
        self.port = port
        self.buff = buff
        self.exitevent = exit_event
        self.migrate_event = migrate_event
        self.blocklen = blocklen
        self.idx = 0
        self.sendlen = sendlen + 1  # >=
        self.ret_code = 1    # sets to 0 when finish properly
        self.debug = debug      # see the self.run_* docstrings for details
        # self.sendidx is the maxiaml number of skipped/duplicated values
        # 1) autoreload when the host socket is reconnected. In this case
        #    it waits <30s for migrate_event and reloads sendidx to sendlen
        # 2) manual write to this value (eg. before you reconnect guest port).
        #    RecvThread decreases this value whenever data loss/dup occurs.
        self.sendidx = -1
        self.minsendidx = self.sendlen

    def reload_loss_idx(self):
        """
        This function reloads the acceptable loss to the original value
        (Reload the self.sendidx to self.sendlen)
        :note: This function is automatically called during port reconnection.
        """
        if self.sendidx >= 0:
            self.minsendidx = min(self.minsendidx, self.sendidx)
            logging.debug("ThRecvCheck %s: Previous data loss was %d.",
                          self.getName(), (self.sendlen - self.sendidx))
        self.sendidx = self.sendlen

    def run(self):
        """ Pick the right mode and execute it """
        if self.debug == 'debug':
            self.run_debug()
        elif self.debug == 'normal' or not self.debug:
            self.run_normal()
        else:
            logging.error('ThRecvCheck %s: Unsupported debug mode, using '
                          'normal mode.', self.getName())
            self.run_normal()

    def run_normal(self):
        """
        Receives data and verifies, whether they match the self.buff (queue).
        It allow data loss up to self.sendidx which can be manually loaded
        after host socket reconnection or you can overwrite this value from
        other thread.
        """
        logging.debug("ThRecvCheck %s: run", self.getName())
        _err_msg_missing_migrate_ev = ("ThRecvCheck %s: Broken pipe. If "
                                       "this is expected behavior set migrate_event to "
                                       "support reconnection." % self.getName())
        _err_msg_exception = ('ThRecvCheck ' + str(self.getName()) + ': Got '
                              'exception %s, continuing')
        _err_msg_disconnect = ('ThRecvCheck ' + str(self.getName()) + ': Port '
                               'disconnected, waiting for new port.')
        _err_msg_reconnect = ('ThRecvCheck ' + str(self.getName()) + ': Port '
                              'reconnected, continuing.')
        attempt = 10
        while not self.exitevent.isSet():
            try:
                ret = select.select([self.port.sock], [], [], 1.0)
            except Exception, inst:
                # self.port is not yet set while reconnecting
                if self.port.sock is None:
                    logging.debug(_err_msg_disconnect)
                    while self.port.sock is None:
                        if self.exitevent.isSet():
                            break
                        time.sleep(0.1)
                    logging.debug(_err_msg_reconnect)
                else:
                    logging.debug(_err_msg_exception, inst)
                continue
            if ret[0] and (not self.exitevent.isSet()):
                try:
                    buf = self.port.sock.recv(self.blocklen)
                except Exception, inst:
                    # self.port is not yet set while reconnecting
                    if self.port.sock is None:
                        logging.debug(_err_msg_disconnect)
                        while self.port.sock is None:
                            if self.exitevent.isSet():
                                break
                            time.sleep(0.1)
                        logging.debug(_err_msg_reconnect)
                    else:
                        logging.debug(_err_msg_exception, inst)
                    continue
                if buf:
                    # Compare the received data with the control data
                    for char in buf:
                        _char = self.buff.popleft()
                        if char == _char:
                            self.idx += 1
                        else:
                            # TODO BUG: data from the socket on host can
                            # be lost during migration
                            while char != _char:
                                if self.sendidx > 0:
                                    self.sendidx -= 1
                                    _char = self.buff.popleft()
                                else:
                                    self.exitevent.set()
                                    logging.error("ThRecvCheck %s: "
                                                  "Failed to recv %dth "
                                                  "character",
                                                  self.getName(), self.idx)
                                    logging.error("ThRecvCheck %s: "
                                                  "%s != %s",
                                                  self.getName(),
                                                  repr(char), repr(_char))
                                    logging.error("ThRecvCheck %s: "
                                                  "Recv = %s",
                                                  self.getName(), repr(buf))
                                    # sender might change the buff :-(
                                    time.sleep(1)
                                    _char = ""
                                    for buf in self.buff:
                                        _char += buf
                                        _char += ' '
                                    logging.error("ThRecvCheck %s: "
                                                  "Queue = %s",
                                                  self.getName(), repr(_char))
                                    logging.info("ThRecvCheck %s: "
                                                 "MaxSendIDX = %d",
                                                 self.getName(),
                                                 (self.sendlen - self.sendidx))
                                    raise error.TestFail("ThRecvCheck %s: "
                                                         "incorrect data" %
                                                         self.getName())
                    attempt = 10
                else:   # ! buf
                    # Broken socket
                    if attempt > 0:
                        attempt -= 1
                        if self.migrate_event is None:
                            self.exitevent.set()
                            raise error.TestFail(_err_msg_missing_migrate_ev)
                        logging.debug("ThRecvCheck %s: Broken pipe "
                                      ", reconnecting. ", self.getName())
                        self.reload_loss_idx()
                        # Wait until main thread sets the new self.port
                        while not (self.exitevent.isSet()
                                   or self.migrate_event.wait(1)):
                            pass
                        if self.exitevent.isSet():
                            break
                        logging.debug("ThRecvCheck %s: Broken pipe resumed, "
                                      "reconnecting...", self.getName())

                        self.port.sock = False
                        self.port.open()
        if self.sendidx >= 0:
            self.minsendidx = min(self.minsendidx, self.sendidx)
        if (self.sendlen - self.minsendidx):
            logging.error("ThRecvCheck %s: Data loss occurred during socket"
                          "reconnection. Maximal loss was %d per one "
                          "migration.", self.getName(),
                          (self.sendlen - self.minsendidx))
        logging.debug("ThRecvCheck %s: exit(%d)", self.getName(),
                      self.idx)
        self.ret_code = 0

    def run_debug(self):
        """
        viz run_normal.
        Additionally it stores last n verified characters and in
        case of failures it quickly receive enough data to verify failure or
        allowed loss and then analyze this data. It provides more info about
        the situation.
        Unlike normal run this one supports booth - loss and duplications.
        It's not friendly to data corruption.
        """
        logging.debug("ThRecvCheck %s: run", self.getName())
        attempt = 10
        max_loss = 0
        sum_loss = 0
        verif_buf = deque(maxlen=max(self.blocklen, self.sendlen))
        while not self.exitevent.isSet():
            ret = select.select([self.port.sock], [], [], 1.0)
            if ret[0] and (not self.exitevent.isSet()):
                buf = self.port.sock.recv(self.blocklen)
                if buf:
                    # Compare the received data with the control data
                    for idx_char in xrange(len(buf)):
                        _char = self.buff.popleft()
                        if buf[idx_char] == _char:
                            self.idx += 1
                            verif_buf.append(_char)
                        else:
                            # Detect the duplicated/lost characters.
                            logging.debug("ThRecvCheck %s: fail to receive "
                                          "%dth character.", self.getName(),
                                          self.idx)
                            buf = buf[idx_char:]
                            for i in xrange(100):
                                if len(self.buff) < self.sendidx:
                                    time.sleep(0.01)
                                else:
                                    break
                            sendidx = min(self.sendidx, len(self.buff))
                            if sendidx < self.sendidx:
                                logging.debug("ThRecvCheck %s: sendidx was "
                                              "lowered as there is not enough "
                                              "data after 1s. Using sendidx="
                                              "%s.", self.getName(), sendidx)
                            for _ in xrange(sendidx / self.blocklen):
                                if self.exitevent.isSet():
                                    break
                                buf += self.port.sock.recv(self.blocklen)
                            queue = _char
                            for _ in xrange(sendidx):
                                queue += self.buff[_]
                            offset_a = None
                            offset_b = None
                            for i in xrange(sendidx):
                                length = min(len(buf[i:]), len(queue))
                                if buf[i:] == queue[:length]:
                                    offset_a = i
                                    break
                            for i in xrange(sendidx):
                                length = min(len(queue[i:]), len(buf))
                                if queue[i:][:length] == buf[:length]:
                                    offset_b = i
                                    break

                            if (offset_b and offset_b < offset_a) or offset_a:
                                # Data duplication
                                self.sendidx -= offset_a
                                max_loss = max(max_loss, offset_a)
                                sum_loss += offset_a
                                logging.debug("ThRecvCheck %s: DUP %s (out of "
                                              "%s)", self.getName(), offset_a,
                                              sendidx)
                                buf = buf[offset_a + 1:]
                                for _ in xrange(len(buf)):
                                    self.buff.popleft()
                                verif_buf.extend(buf)
                                self.idx += len(buf)
                            elif offset_b:  # Data loss
                                max_loss = max(max_loss, offset_b)
                                sum_loss += offset_b
                                logging.debug("ThRecvCheck %s: LOST %s (out of"
                                              " %s)", self.getName(), offset_b,
                                              sendidx)
                                # Pop-out the lost characters from verif_queue
                                # (first one is already out)
                                self.sendidx -= offset_b
                                for i in xrange(offset_b - 1):
                                    self.buff.popleft()
                                for _ in xrange(len(buf)):
                                    self.buff.popleft()
                                self.idx += len(buf)
                                verif_buf.extend(buf)
                            else:   # Too big data loss or duplication
                                verif = ""
                                for _ in xrange(-min(sendidx, len(verif_buf)),
                                                0):
                                    verif += verif_buf[_]
                                logging.error("ThRecvCheck %s: mismatched data"
                                              ":\nverified: ..%s\nreceived:   "
                                              "%s\nsent:       %s",
                                              self.getName(), repr(verif),
                                              repr(buf), repr(queue))
                                raise error.TestFail("Recv and sendqueue "
                                                     "don't match with any offset.")
                            # buf was changed, break from this loop
                            attempt = 10
                            break
                    attempt = 10
                else:   # ! buf
                    # Broken socket
                    if attempt > 0:
                        attempt -= 1
                        if self.migrate_event is None:
                            self.exitevent.set()
                            raise error.TestFail("ThRecvCheck %s: Broken pipe."
                                                 " If this is expected behavior set migrate"
                                                 "_event to support reconnection." %
                                                 self.getName())
                        logging.debug("ThRecvCheck %s: Broken pipe "
                                      ", reconnecting. ", self.getName())
                        self.reload_loss_idx()
                        # Wait until main thread sets the new self.port
                        while not (self.exitevent.isSet()
                                   or self.migrate_event.wait(1)):
                            pass
                        if self.exitevent.isSet():
                            break
                        logging.debug("ThRecvCheck %s: Broken pipe resumed, "
                                      "reconnecting...", self.getName())

                        self.port.sock = False
                        self.port.open()
        if self.sendidx >= 0:
            self.minsendidx = min(self.minsendidx, self.sendidx)
        if (self.sendlen - self.minsendidx):
            logging.debug("ThRecvCheck %s: Data loss occurred during socket"
                          "reconnection. Maximal loss was %d per one "
                          "migration.", self.getName(),
                          (self.sendlen - self.minsendidx))
        if sum_loss > 0:
            logging.debug("ThRecvCheck %s: Data offset detected, cumulative "
                          "err: %d, max err: %d(%d)", self.getName(), sum_loss,
                          max_loss, float(max_loss) / self.blocklen)
        logging.debug("ThRecvCheck %s: exit(%d)", self.getName(),
                      self.idx)
        self.ret_code = 0
