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

from avocado import aexpect
from avocado.utils import crypto
from avocado.utils import network as base_network
from avocado.utils import params as my_params
from avocado.machine.virtual.base import VirtualMachine
from avocado.virt.utils import network
from avocado.virt.qemu import cmdline
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

    def create(self):
        devices = self.cmdline_assembler.assemble()
        print devices.cmdline()
        qemu_cmdline = devices.cmdline()
        self.process = aexpect.run_tail(qemu_cmdline,
                                        None,
                                        log.info,
                                        "[qemu output]",
                                        auto_close=False)
        log.info("Created qemu process with parent PID %d",
                 self.process.get_pid())

    def needs_restart(self):
        return False

    def destroy(self):
        pass


def create_from_cmdline(cmdline):
    pass
