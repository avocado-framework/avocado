import base
import baremetal
import virtual

mapping = {'generic': base.Machine,
           'baremetal': baremetal.base.BareMetalMachine,
           'virtual-generic': virtual.base.VirtualMachine,
           'virtual-qemu': virtual.qemu.QemuVirtualMachine}
