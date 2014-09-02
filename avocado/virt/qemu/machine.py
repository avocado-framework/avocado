import os
import socket
import string
import logging
import tempfile
import uuid

from avocado.core import exceptions
from avocado import aexpect
from avocado.utils import io
from avocado.utils import network
from avocado.utils import process
from avocado.utils import remote
from avocado.utils import wait

from avocado.virt.qemu import monitor
from avocado.virt.qemu import devices
from avocado.virt.qemu import path

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
        self.uuid = uuid.uuid4()

    def __str__(self):
        uuid = str(self.uuid)
        return 'QEMU VM (%s)' % uuid[:8]

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

    def setup_remote_login(self, hostname=None, username=None, password=None, port=22):
        if not self.logged:
            self.log('Setting up remote login')
            hostname = socket.gethostbyname(socket.gethostname())
            username = self.params.get('remote_username', 'root')
            password = self.params.get('remote_password', '123456')
            port = self.devices.redir_port
            self.remote = remote.Remote(hostname, username, password, port)
            res = self.remote.uptime()
            if res.succeeded:
                self.logged = True

    def clone(self, params=None):
        new_vm = VM(self.params)
        new_vm.devices = self.devices.clone(params)
        return new_vm

    def migrate(self, migration_mode='tcp'):
        def migrate_finish():
            mig_info = self.qmp("query-migrate")
            return mig_info['return']['status'] != 'active'

        def migrate_success():
            mig_info = self.qmp("query-migrate")
            return mig_info['return']['status'] == 'completed'

        def migrate_fail():
            mig_info = self.qmp("query-migrate")
            return mig_info['return']['status'] == 'failed'

        clone_params = self.params.copy()
        clone_params['qemu_bin'] = path.get_qemu_dst_binary(clone_params)
        clone = self.clone(clone_params)
        migration_port = clone.devices.redir_port + 1
        while not network.is_port_free(migration_port, 'localhost'):
            migration_port += 1
        incoming_args = " -incoming %s:0:%d" % (migration_mode, migration_port)
        clone.devices.add_args(incoming_args)
        clone.launch()
        uri = "%s:localhost:%d" % (migration_mode, migration_port)
        self.qmp("migrate", uri=uri)
        wait.wait_for(migrate_finish, timeout=60,
                      text='Waiting for migration to complete')
        if migrate_success():
            self.log("Migration successful")
        else:
            raise exceptions.TestFail("Migration of %s failed" % self)
        old_vm = VM()
        old_vm.__dict__ = self.__dict__
        self.__dict__ = clone.__dict__
        old_vm.shutdown()
