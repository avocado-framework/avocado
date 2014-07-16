"""
Contains the QEMU virtual machine class.

QEMU is a widely used open source machine emulator and virtualizer. The
QemuVirtualMachine class provides an abstraction model for interacting with
qemu processses as virtual machine objects, which you can control (start, stop,
migrate, so on and so forth). We also provide convenience methods to run your
own qemu commands made from scratch and then providing the same conveniences.
"""

import logging
import time
import glob
import os

from avocado import aexpect
from avocado.utils import crypto
from avocado.utils import network as base_network
from avocado.utils import params as my_params
from avocado.machine.virtual.base import VirtualMachine
from avocado.virt import exceptions
from avocado.virt.utils import network
from avocado.virt.qemu import cmdline
from avocado.virt.qemu import monitor
from avocado.virt.qemu import path as q_path

log = logging.getLogger("avocado.test")


class CpuInfo(object):

    """
    A class for VM's cpu information.
    """

    def __init__(self, model=None, vendor=None, flags=None, family=None,
                 smp=0, maxcpus=0, sockets=0, cores=0, threads=0):
        """
        :param model: CPU Model of VM (use 'qemu -cpu ?' for list)
        :param vendor: CPU Vendor of VM
        :param flags: CPU Flags of VM
        :param flags: CPU Family of VM
        :param smp: set the number of CPUs to 'n' [default=1]
        :param maxcpus: maximum number of total cpus, including
                        offline CPUs for hotplug, etc
        :param cores: number of CPU cores on one socket
        :param threads: number of threads on one CPU core
        :param sockets: number of discrete sockets in the system
        """
        self.model = model
        self.vendor = vendor
        self.flags = flags
        self.family = family
        self.smp = smp
        self.maxcpus = maxcpus
        self.sockets = sockets
        self.cores = cores
        self.threads = threads


class QemuVirtualMachine(VirtualMachine):
    MIGRATION_PROTOS = ['rdma', 'x-rdma', 'tcp', 'unix', 'exec', 'fd']

    # By default we inherit all timeouts from the base VM class except...
    CLOSE_SESSION_TIMEOUT = 30

    # Because we've seen qemu taking longer than 5 seconds to initialize
    # itself completely, including creating the monitor sockets files
    # which are used on create(), this timeout is considerably larger
    # than the one on the base vm class
    CREATE_TIMEOUT = 20

    def __init__(self, params, name):
        self.params = my_params.Params(params)
        self.name = name
        self.pci_addr_list = [0, 1, 2]
        self.qemu_binary = q_path.get_qemu_binary(params)
        self._generate_unique_id()
        self.cmdline_assembler = cmdline.QemuCmdLine(self.params, self)
        if hasattr(self, 'virtnet'):
            getattr(self, 'virtnet').__init__(self.params,
                                              self.name,
                                              self.instance)
        else:
            self.virtnet = network.VirtNet(self.params,
                                           self.name,
                                           self.instance)
        self.cpuinfo = CpuInfo()
        self.vnc_port = base_network.find_free_port(5900, 6100)

    def _generate_unique_id(self):
        """
        Generate a unique identifier for this VM
        """
        while True:
            self.instance = (time.strftime("%Y%m%d-%H%M%S-") +
                             crypto.get_random_string(8))
            if not glob.glob("/tmp/*%s" % self.instance):
                break

    def get_serial_console_filename(self, name=None):
        """
        Return the serial console filename.

        :param name: The serial port name.
        """
        if name:
            return "/tmp/serial-%s-%s" % (name, self.instance)
        return "/tmp/serial-%s" % self.instance

    def _clear_virtnet_fd(self):
        # test doesn't need to hold tapfd's open
        for nic in self.virtnet:
            if 'tapfds' in nic:  # implies bridge/tap
                try:
                    for i in nic.tapfds.split(':'):
                        os.close(int(i))
                    # qemu process retains access via open file
                    # remove this attribute from virtnet because
                    # fd numbers are not always predictable and
                    # vm instance must support cloning.
                    del nic['tapfds']
                # File descriptor is already closed
                except OSError:
                    pass
            if 'vhostfds' in nic:
                try:
                    for i in nic.vhostfds.split(':'):
                        os.close(int(i))
                    del nic['vhostfds']
                except OSError:
                    pass

    def create(self, migration_mode=None):
        devices = self.cmdline_assembler.assemble()
        qemu_cmdline = devices.cmdline()
        self.process = aexpect.run_tail(qemu_cmdline,
                                        None,
                                        log.info,
                                        "[qemu output]",
                                        auto_close=False)
        log.info("Created qemu process with parent PID %d",
                 self.process.get_pid())

        self._clear_virtnet_fd()

        # Make sure qemu is not defunct
        if self.process.is_defunct():
            logging.error("Bad things happened, qemu process is defunct")
            err = ("Qemu is defunct.\nQemu output:\n%s"
                   % self.process.get_output())
            self.destroy()
            raise exceptions.VMStartError(self.name, err)

        # Make sure the process was started successfully
        if not self.process.is_alive():
            status = self.process.get_status()
            output = self.process.get_output().strip()
            migration_in_course = migration_mode is not None
            unknown_protocol = "unknown migration protocol" in output
            if migration_in_course and unknown_protocol:
                e = exceptions.VMMigrateProtoUnsupportedError(migration_mode, output)
            else:
                e = exceptions.VMCreateError(qemu_cmdline, status, output)
            self.destroy()
            raise e

        # Establish monitor connections
        self.monitors = []
        for monitor_name in self.params.objects("monitors"):
            monitor_params = self.params.object_params(monitor_name)
            try:
                monitor = monitor.wait_for_create_monitor(self, monitor_name, monitor_params, self.CREATE_TIMEOUT)
            except monitor.MonitorConnectError, detail:
                logging.error(detail)
                self.destroy()
                raise

            # Add this monitor to the list
            self.monitors += [monitor]

        # Create isa serial ports.
        for serial in self.params.objects("isa_serials"):
            self.serial_ports.append(serial)

    def needs_restart(self):
        return False

    def destroy(self):
        pass


def create_from_cmdline(cmdline):
    pass
