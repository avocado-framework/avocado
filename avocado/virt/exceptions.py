import logging
from avocado.core import exceptions

log = logging.getLogger("avocado.test")


class VMError(Exception):
    pass


class VMCreateError(VMError):

    def __init__(self, cmd, status, output):
        VMError.__init__(self, cmd, status, output)
        self.cmd = cmd
        self.status = status
        self.output = output

    def __str__(self):
        return ("VM creation command failed:    %r    (status: %s,    "
                "output: %r)" % (self.cmd, self.status, self.output))


class VMStartError(VMError):

    def __init__(self, name, reason=None):
        VMError.__init__(self, name, reason)
        self.name = name
        self.reason = reason

    def __str__(self):
        msg = "VM '%s' failed to start" % self.name
        if self.reason is not None:
            msg += ": %s" % self.reason
        return msg


class VMConfigMissingError(VMError):

    def __init__(self, name, config):
        VMError.__init__(self, name, config)
        self.name = name
        self.config = config

    def __str__(self):
        return "Missing config '%s' for VM %s" % (self.config, self.name)


class VMHashMismatchError(VMError):

    def __init__(self, actual, expected):
        VMError.__init__(self, actual, expected)
        self.actual_hash = actual
        self.expected_hash = expected

    def __str__(self):
        return ("CD image hash (%s) differs from expected one (%s)" %
                (self.actual_hash, self.expected_hash))


class VMImageMissingError(VMError):

    def __init__(self, filename):
        VMError.__init__(self, filename)
        self.filename = filename

    def __str__(self):
        return "CD image file not found: %r" % self.filename


class VMImageCheckError(VMError):

    def __init__(self, filename):
        VMError.__init__(self, filename)
        self.filename = filename

    def __str__(self):
        return "Errors found on image: %r" % self.filename


class VMBadPATypeError(VMError):

    def __init__(self, pa_type):
        VMError.__init__(self, pa_type)
        self.pa_type = pa_type

    def __str__(self):
        return "Unsupported PCI assignable type: %r" % self.pa_type


class VMPAError(VMError):

    def __init__(self, pa_type):
        VMError.__init__(self, pa_type)
        self.pa_type = pa_type

    def __str__(self):
        return ("No PCI assignable devices could be assigned "
                "(pci_assignable=%r)" % self.pa_type)


class VMPostCreateError(VMError):

    def __init__(self, cmd, output):
        VMError.__init__(self, cmd, output)
        self.cmd = cmd
        self.output = output


class VMHugePageError(VMPostCreateError):

    def __str__(self):
        return ("Cannot allocate hugepage memory    (command: %r,    "
                "output: %r)" % (self.cmd, self.output))


class VMKVMInitError(VMPostCreateError):

    def __str__(self):
        return ("Cannot initialize KVM    (command: %r,    output: %r)" %
                (self.cmd, self.output))


class VMDeadError(VMError):

    def __init__(self, reason='', detail=''):
        VMError.__init__(self)
        self.reason = reason
        self.detail = detail

    def __str__(self):
        msg = "VM is dead"
        if self.reason:
            msg += "    reason: %s" % self.reason
        if self.detail:
            msg += "    detail: %r" % self.detail
        return (msg)


class VMDeadKernelCrashError(VMError):

    def __init__(self, kernel_crash):
        VMError.__init__(self, kernel_crash)
        log.debug(kernel_crash)

    def __str__(self):
        return ("VM is dead due to a kernel crash, "
                "see debug/serial log for details")


class VMInvalidInstructionCode(VMError):

    def __init__(self, invalid_code):
        VMError.__init__(self, invalid_code)
        self.invalid_code = invalid_code

    def __str__(self):
        error = ""
        for invalid_code in self.invalid_code:
            error += "%s" % (invalid_code)
        return ("Invalid instruction was executed on VM:\n%s" % error)


class VMAddressError(VMError):
    pass


class VMInterfaceIndexError(VMError):
    pass


class VMPortNotRedirectedError(VMAddressError):

    def __init__(self, port, virtnet_nic=None):
        VMAddressError.__init__(self, port)
        self.port = port
        self.virtnet_nic = virtnet_nic

    def __str__(self):
        msg = "Don't know how to connect to guest port %s" % self.port
        if self.virtnet_nic is None:
            return msg
        else:
            nic = self.virtnet_nic
            msg += (" with networking type '%s', to destination '%s', for nic "
                    "'%s' with mac '%s' and ip '%s'." % (nic.nettype, nic.netdst,
                                                         nic.nic_name, nic.mac, nic.ip))
            return msg


class VMAddressVerificationError(VMAddressError):

    def __init__(self, mac, ip):
        VMAddressError.__init__(self, mac, ip)
        self.mac = mac
        self.ip = ip

    def __str__(self):
        return ("Could not verify DHCP lease: "
                "%s --> %s" % (self.mac, self.ip))


class VMMACAddressMissingError(VMAddressError):

    def __init__(self, nic_index):
        VMAddressError.__init__(self, nic_index)
        self.nic_index = nic_index

    def __str__(self):
        return "No MAC defined for NIC #%s" % self.nic_index


class VMIPAddressMissingError(VMAddressError):

    def __init__(self, mac, ip_version="ipv4"):
        VMAddressError.__init__(self, mac)
        self.mac = mac
        self.ip_version = ip_version

    def __str__(self):
        return "No %s DHCP lease for MAC %s" % (self.ip_version, self.mac)


class VMUnknownNetTypeError(VMError):

    def __init__(self, vmname, nicname, nettype):
        super(VMUnknownNetTypeError, self).__init__()
        self.vmname = vmname
        self.nicname = nicname
        self.nettype = nettype

    def __str__(self):
        return "Unknown nettype '%s' requested for NIC %s on VM %s" % (
            self.nettype, self.nicname, self.vmname)


class VMAddNetDevError(VMError):
    pass


class VMDelNetDevError(VMError):
    pass


class VMAddNicError(VMError):
    pass


class VMDelNicError(VMError):
    pass


class VMMigrateError(VMError):
    pass


class VMMigrateTimeoutError(VMMigrateError):
    pass


class VMMigrateCancelError(VMMigrateError):
    pass


class VMMigrateFailedError(VMMigrateError):
    pass


class VMMigrateProtoUnknownError(exceptions.TestNAError):

    def __init__(self, protocol):
        self.protocol = protocol

    def __str__(self):
        return ("Virt Test doesn't know migration protocol '%s'. "
                "You would have to add it to the list of known protocols" %
                self.protocol)


class VMMigrateStateMismatchError(VMMigrateError):

    def __init__(self):
        VMMigrateError.__init__(self)

    def __str__(self):
        return ("Mismatch of VM state before and after migration")


class VMRebootError(VMError):
    pass


class VMStatusError(VMError):
    pass


class VMRemoveError(VMError):
    pass


class VMDeviceError(VMError):
    pass


class VMDeviceNotSupportedError(VMDeviceError):

    def __init__(self, name, device):
        VMDeviceError.__init__(self, name, device)
        self.name = name
        self.device = device

    def __str__(self):
        return ("Device '%s' is not supported for vm '%s' on this Host." %
                (self.device, self.name))


class VMPCIDeviceError(VMDeviceError):
    pass


class VMPCISlotInUseError(VMPCIDeviceError):

    def __init__(self, name, slot):
        VMPCIDeviceError.__init__(self, name, slot)
        self.name = name
        self.slot = slot

    def __str__(self):
        return ("PCI slot '0x%s' is already in use on vm '%s'. Please assign"
                " another slot in config file." % (self.slot, self.name))


class VMPCIOutOfRangeError(VMPCIDeviceError):

    def __init__(self, name, max_dev_num):
        VMPCIDeviceError.__init__(self, name, max_dev_num)
        self.name = name
        self.max_dev_num = max_dev_num

    def __str__(self):
        return ("Too many PCI devices added on vm '%s', max supported '%s'" %
                (self.name, str(self.max_dev_num)))


class VMUSBError(VMError):
    pass


class VMUSBControllerError(VMUSBError):
    pass


class VMUSBControllerMissingError(VMUSBControllerError):

    def __init__(self, name, controller_type):
        VMUSBControllerError.__init__(self, name, controller_type)
        self.name = name
        self.controller_type = controller_type

    def __str__(self):
        return ("Could not find '%s' USB Controller on vm '%s'. Please "
                "check config files." % (self.controller_type, self.name))


class VMUSBControllerPortFullError(VMUSBControllerError):

    def __init__(self, name, usb_dev_dict):
        VMUSBControllerError.__init__(self, name, usb_dev_dict)
        self.name = name
        self.usb_dev_dict = usb_dev_dict

    def __str__(self):
        output = ""
        try:
            for ctl, dev_list in self.usb_dev_dict.iteritems():
                output += "%s: %s\n" % (ctl, dev_list)
        except Exception:
            pass

        return ("No available USB port left on VM %s.\n"
                "USB devices map is: \n%s" % (self.name, output))


class VMUSBPortInUseError(VMUSBError):

    def __init__(self, vm_name, controller, port):
        VMUSBError.__init__(self, vm_name, controller, port)
        self.vm_name = vm_name
        self.controller = controller
        self.port = port

    def __str__(self):
        return ("USB port '%d' of controller '%s' is already in use on vm"
                " '%s'. Please assign another port in config file." %
                (self.port, self.controller, self.vm_name))


class VMScreenInactiveError(VMError):

    def __init__(self, vm, inactive_time):
        VMError.__init__(self)
        self.vm = vm
        self.inactive_time = inactive_time

    def __str__(self):
        msg = ("%s screen is inactive for %d s (%d min)" %
               (self.vm.name, self.inactive_time, self.inactive_time / 60))
        return msg
