"""
Contains the QEMU virtual machine class.

QEMU is a widely used open source machine emulator and virtualizer. The
QemuVirtualMachine class provides an abstraction model for interacting with
qemu processses as virtual machine objects, which you can control (start, stop,
migrate, so on and so forth). We also provide convenience methods to run your
own qemu commands made from scratch and then providing the same conveniences.
"""

from avocado.machine.virtual.base import VirtualMachine


class QemuVirtualMachine(VirtualMachine):

    def __init__(self, params):
        self.params = params
        # init value by default.
        # PCI addr 0,1,2 are taken by PCI/ISA/IDE bridge and the GPU.
        self.pci_addr_list = [0, 1, 2]


def create_from_cmdline(cmdline):
    pass
