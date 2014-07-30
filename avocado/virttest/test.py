from avocado import test
from avocado.virttest import virt_vm


class VirtTest(test.Test):

    def create_vm(self, name):
        """
        Start a VM with the current test params.

        :param name: VM name (ex virt-tests-vm1).
        """
        vm_type = self.params.get('vm_type', 'qemu')
        target = self.params.get('target')
        vm_class = virt_vm.BaseVM.lookup_vm_class(vm_type, target)
        if vm_class is not None:
            vm = vm_class(name, self.params, self.basedir,
                          self.params.get("address_cache"))
            vm.create()
            vm.verify_alive()
            vm.resume()
            return vm
