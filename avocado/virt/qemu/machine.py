import os
import string
import logging
import tempfile

from avocado import aexpect
from avocado.utils import io
from avocado.utils import process
from avocado.utils import remote

from avocado.virt.qemu import monitor
from avocado.virt.qemu import devices

log = logging.getLogger("avocado.test")


class VM(object):

    """
    Represents a QEMU Virtual Machine
    """

    def __init__(self, params=None):
        self._popen = None
        self.params = params
        self.devices = devices.QemuDevices(params)
        self.logged = False
        self.remote = None

    def __str__(self):
        return 'QEMU VM (%#x)' % id(self)

    def log(self, msg):
        log.info('%s %s' % (self, msg))

    def launch(self):
        assert self._popen is None

        self.monitor_socket = tempfile.mktemp()
        self.devices.add_qmp_monitor(self.monitor_socket)
        self._qmp = monitor.QEMUMonitorProtocol(self.monitor_socket,
                                                server=True)
        self.serial_socket = tempfile.mktemp()
        self.devices.add_serial(self.serial_socket)
        cmdline = self.devices.get_cmdline()

        try:
            self._popen = process.SubProcess(cmd=cmdline)
            self._qmp.accept()
            self.serial_console = aexpect.ShellSession(
                "nc -U %s" % self.serial_socket,
                auto_close=False,
                output_func=io.log_line,
                output_params=("serial-console-%#x.log" % id(self),),
                prompt=self.params.get("shell_prompt", "[\#\$]"))
        finally:
            os.remove(self.monitor_socket)

    def shutdown(self):
        if self._popen is not None:
            self._qmp.cmd('quit')
            self._popen.wait()
            self._popen = None
            self.log('Shut down')

    def __enter__(self):
        self.launch()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False

    def qmp(self, cmd, **args):
        qmp_args = dict()
        for k in args.keys():
            qmp_args[k.translate(string.maketrans('_', '-'))] = args[k]

        self.log("-> QMP %s %s" % (cmd, qmp_args))
        retval = self._qmp.cmd(cmd, args=qmp_args)
        self.log("<- QMP %s" % retval)
        return retval

    def get_qmp_event(self, wait=False):
        return self._qmp.pull_event(wait=wait)

    def get_qmp_events(self, wait=False):
        events = self._qmp.get_events(wait=wait)
        self._qmp.clear_events()
        return events

    def hmp_qemu_io(self, drive, cmd):
        return self.qmp('human-monitor-command',
                        command_line='qemu-io %s "%s"' % (drive, cmd))

    def pause_drive(self, drive, event=None):
        if event is None:
            self.pause_drive(drive, "read_aio")
            self.pause_drive(drive, "write_aio")
            return
        self.hmp_qemu_io(drive, 'break %s bp_%s' % (event, drive))

    def resume_drive(self, drive):
        self.hmp_qemu_io(drive, 'remove_break bp_%s' % drive)

    def setup_remote_login(self, hostname, username, password=None, port=22):
        if not self.logged:
            self.remote = remote.Remote(hostname, username, password, port)
            res = self.remote.uptime()
            if res.succeeded:
                self.logged = True
