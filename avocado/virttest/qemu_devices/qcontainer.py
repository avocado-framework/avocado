"""
Autotest qdev-structure representation.

This is the main class which represent qdev-structure. It allows to create,
interact and verify the qemu qdev structure.

:copyright: 2012-2013 Red Hat Inc.
"""

# Python imports
import logging
import re

# Autotest imports
from autotest.client.shared import utils, error
from virttest import arch, storage, data_dir, virt_vm
from utils import (DeviceError, DeviceHotplugError, DeviceInsertError,
                   DeviceRemoveError, DeviceUnplugError, none_or_int)
import os
import qbuses
import qdevices


#
# Device container (device representation of VM)
# This class represents VM by storing all devices and their connections (buses)
#
class DevContainer(object):

    """
    Device container class
    """
    # General methods

    def __init__(self, qemu_binary, vmname, strict_mode="no",
                 workaround_qemu_qmp_crash="no", allow_hotplugged_vm="yes"):
        """
        :param qemu_binary: qemu binary
        :param vm: related VM
        :param strict_mode: Use strict mode (set optional params)
        """
        def get_hmp_cmds(qemu_binary):
            """ :return: list of human monitor commands """
            _ = utils.system_output("echo -e 'help\nquit' | %s -monitor "
                                    "stdio -vnc none" % qemu_binary,
                                    timeout=10, ignore_status=True)
            _ = re.findall(r'^([^\| \[\n]+\|?\w+)', _, re.M)
            hmp_cmds = []
            for cmd in _:
                if '|' not in cmd:
                    if cmd != 'The':
                        hmp_cmds.append(cmd)
                else:
                    hmp_cmds.extend(cmd.split('|'))
            return hmp_cmds

        def get_qmp_cmds(qemu_binary, workaround_qemu_qmp_crash=False):
            """ :return: list of qmp commands """
            cmds = None
            if not workaround_qemu_qmp_crash:
                cmds = utils.system_output('echo -e \''
                                           '{ "execute": "qmp_capabilities" }\n'
                                           '{ "execute": "query-commands", "id": "RAND91" }\n'
                                           '{ "execute": "quit" }\''
                                           '| %s -qmp stdio -vnc none | grep return |'
                                           ' grep RAND91' % qemu_binary, timeout=10,
                                           ignore_status=True).splitlines()
            if not cmds:
                # Some qemu versions crashes when qmp used too early; add sleep
                cmds = utils.system_output('echo -e \''
                                           '{ "execute": "qmp_capabilities" }\n'
                                           '{ "execute": "query-commands", "id": "RAND91" }\n'
                                           '{ "execute": "quit" }\' | (sleep 1; cat )'
                                           '| %s -qmp stdio -vnc none | grep return |'
                                           ' grep RAND91' % qemu_binary, timeout=10,
                                           ignore_status=True).splitlines()
            if cmds:
                cmds = re.findall(r'{\s*"name"\s*:\s*"([^"]+)"\s*}', cmds[0])
            if cmds:    # If no mathes, return None
                return cmds

        self.__state = -1    # -1 synchronized, 0 synchronized after hotplug
        self.__qemu_help = utils.system_output("%s -help" % qemu_binary,
                                               timeout=10, ignore_status=True)
        self.__device_help = utils.system_output("%s -device ? 2>&1"
                                                 % qemu_binary, timeout=10,
                                                 ignore_status=True)
        self.__machine_types = utils.system_output("%s -M ?" % qemu_binary,
                                                   timeout=10, ignore_status=True)
        self.__hmp_cmds = get_hmp_cmds(qemu_binary)
        self.__qmp_cmds = get_qmp_cmds(qemu_binary,
                                       workaround_qemu_qmp_crash == 'always')
        self.vmname = vmname
        self.strict_mode = strict_mode == 'yes'
        self.__devices = []
        self.__buses = []
        self.__qemu_binary = qemu_binary
        self.__execute_qemu_last = None
        self.__execute_qemu_out = ""
        self.allow_hotplugged_vm = allow_hotplugged_vm == 'yes'

    def __getitem__(self, item):
        """
        :param item: autotest id or QObject-like object
        :return: First matching object defined in this QDevContainer
        :raise KeyError: In case no match was found
        """
        if isinstance(item, qdevices.QBaseDevice):
            if item in self.__devices:
                return item
        elif item:
            for device in self.__devices:
                if device.get_aid() == item:
                    return device
        raise KeyError("Device %s is not in %s" % (item, self))

    def get(self, item):
        """
        :param item: autotest id or QObject-like object
        :return: First matching object defined in this QDevContainer or None
        """
        if item in self:
            return self[item]

    def get_by_properties(self, filt):
        """
        Return list of matching devices
        :param filt: filter {'property': 'value', ...}
        :type filt: dict
        """
        out = []
        for device in self.__devices:
            for key, value in filt.iteritems():
                if not hasattr(device, key):
                    break
                if getattr(device, key) != value:
                    break
            else:
                out.append(device)
        return out

    def get_by_params(self, filt):
        """
        Return list of matching devices
        :param filt: filter {'param': 'value', ...}
        :type filt: dict
        """
        out = []
        for device in self.__devices:
            for key, value in filt.iteritems():
                if key not in device.params:
                    break
                if device.params[key] != value:
                    break
            else:
                out.append(device)
        return out

    def __delitem__(self, item):
        """
        Delete specified item from devices list
        :param item: autotest id or QObject-like object
        :raise KeyError: In case no match was found
        """
        # Remove child_buses including devices
        if self.remove(item):
            raise KeyError(item)

    def remove(self, device, recursive=True):
        """
        Remove device from this representation
        :param device: autotest id or QObject-like object
        :param recursive: remove children recursively
        :return: None on success, -1 when the device is not present
        """
        device = self[device]
        if not recursive:   # Check if there are no children
            for bus in device.child_bus:
                if len(bus) != 0:
                    raise DeviceRemoveError(device, "Child bus contains "
                                            "devices", self)
        else:               # Recursively remove all devices
            for dev in device.get_children():
                # One child might be already removed from other child's bus
                if dev in self:
                    self.remove(dev, True)
        if device in self.__devices:    # It might be removed from child bus
            for bus in self.__buses:        # Remove from parent_buses
                bus.remove(device)
            for bus in device.child_bus:    # Remove child buses from vm buses
                self.__buses.remove(bus)
            self.__devices.remove(device)   # Remove from list of devices

    def wash_the_device_out(self, device):
        """
        Removes any traces of the device from representation.
        :param device: qdevices.QBaseDevice device
        """
        # remove device from parent buses
        for bus in self.__buses:
            if device in bus:
                bus.remove(device)
        # remove child devices
        for bus in device.child_bus:
            for dev in device.get_children():
                if dev in self:
                    self.remove(dev, True)
            # remove child_buses from self.__buses
            if bus in self.__buses:
                self.__buses.remove(bus)
        # remove device from self.__devices
        if device in self.__devices:
            self.__devices.remove(device)

    def __len__(self):
        """ :return: Number of inserted devices """
        return len(self.__devices)

    def __contains__(self, item):
        """
        Is specified item defined in current devices list?
        :param item: autotest id or QObject-like object
        :return: True - yes, False - no
        """
        if isinstance(item, qdevices.QBaseDevice):
            if item in self.__devices:
                return True
        elif item:
            for device in self.__devices:
                if device.get_aid() == item:
                    return True
        return False

    def __iter__(self):
        """ Iterate over all defined devices. """
        return self.__devices.__iter__()

    def __eq__(self, qdev2):
        """ Are the VM representation alike? """
        if len(qdev2) != len(self):
            return False
        if qdev2.get_state() != self.get_state():
            if qdev2.allow_hotplugged_vm:
                if qdev2.get_state() > 0 or self.get_state() > 0:
                    return False
            else:
                return False
        for dev in self:
            if dev not in qdev2:
                return False

        # state, buses and devices are handled earlier
        qdev2 = qdev2.__dict__
        for key, value in self.__dict__.iteritems():
            if key in ("_DevContainer__devices", "_DevContainer__buses",
                       "_DevContainer__state",
                       "allow_hotplugged_vm"):
                continue
            if key not in qdev2 or qdev2[key] != value:
                return False
        return True

    def __ne__(self, qdev2):
        """ Are the VM representation different? """
        return not self.__eq__(qdev2)

    def set_dirty(self):
        """ Increase VM dirtiness (not synchronized with VM) """
        if self.__state >= 0:
            self.__state += 1
        else:
            self.__state = 1

    def set_clean(self):
        """ Decrease VM dirtiness (synchronized with VM) """
        if self.__state > 0:
            self.__state -= 1
        else:
            raise DeviceError("Trying to clean clear VM (probably calling "
                              "hotplug_clean() twice).\n%s" % self.str_long())

    def reset_state(self):
        """
        Mark representation as completely clean, without hotplugged devices.
        """
        self.__state = -1

    def get_state(self):
        """ Get the current state (0 = synchronized with VM) """
        return self.__state

    def get_by_qid(self, qid):
        """
        :param qid: qemu id
        :return: List of items with matching qemu id
        """
        ret = []
        if qid:
            for device in self:
                if device.get_qid() == qid:
                    ret.append(device)
        return ret

    def str_short(self):
        """ Short string representation of all devices """
        out = "Devices of %s" % self.vmname
        dirty = self.get_state()
        if dirty == -1:
            pass
        elif dirty == 0:
            out += "(H)"
        else:
            out += "(DIRTY%s)" % dirty
        out += ": ["
        for device in self:
            out += "%s," % device
        if out[-1] == ',':
            out = out[:-1]
        return out + "]"

    def str_long(self):
        """ Long string representation of all devices """
        out = "Devices of %s" % self.vmname
        dirty = self.get_state()
        if dirty == -1:
            pass
        elif dirty == 0:
            out += "(H)"
        else:
            out += "(DIRTY%s)" % dirty
        out += ":\n"
        for device in self:
            out += device.str_long()
        if out[-1] == '\n':
            out = out[:-1]
        return out

    def str_bus_short(self):
        """ Short representation of all buses """
        out = "Buses of %s\n  " % self.vmname
        for bus in self.__buses:
            out += str(bus)
            out += "\n  "
        return out[:-3]

    def str_bus_long(self):
        """ Long representation of all buses """
        out = "Devices of %s:\n  " % self.vmname
        for bus in self.__buses:
            out += bus.str_long().replace('\n', '\n  ')
        return out[:-3]

    def __create_unique_aid(self, qid):
        """
        Creates unique autotest id name from given qid
        :param qid: Original qemu id
        :return: aid (the format is "$qid__%d")
        """
        if qid and qid not in self:
            return qid
        i = 0
        while "%s__%d" % (qid, i) in self:
            i += 1
        return "%s__%d" % (qid, i)

    def has_option(self, option):
        """
        :param option: Desired option
        :return: Is the desired option supported by current qemu?
        """
        return bool(re.search(r"^-%s(\s|$)" % option, self.__qemu_help,
                              re.MULTILINE))

    def has_device(self, device):
        """
        :param device: Desired device
        :return: Is the desired device supported by current qemu?
        """
        return bool(re.search(r'name "%s"|alias "%s"' % (device, device),
                              self.__device_help))

    def get_help_text(self):
        """
        :return: Full output of "qemu -help"
        """
        return self.__qemu_help

    def has_hmp_cmd(self, cmd):
        """
        :param cmd: Desired command
        :return: Is the desired command supported by this qemu's human monitor?
        """
        return cmd in self.__hmp_cmds

    def has_qmp_cmd(self, cmd):
        """
        :param cmd: Desired command
        :return: Is the desired command supported by this qemu's QMP monitor?
        """
        return cmd in self.__qmp_cmds

    def execute_qemu(self, options, timeout=5):
        """
        Execute this qemu and return the stdout+stderr output.
        :param options: additional qemu options
        :type options: string
        :param timeout: execution timeout
        :type timeout: int
        :return: Output of the qemu
        :rtype: string
        """
        if self.__execute_qemu_last != options:
            cmd = "%s %s 2>&1" % (self.__qemu_binary, options)
            self.__execute_qemu_out = str(utils.run(cmd, timeout=timeout,
                                                    ignore_status=True,
                                                    verbose=False).stdout)
        return self.__execute_qemu_out

    def get_buses(self, bus_spec, type_test=False):
        """
        :param bus_spec: Bus specification (dictionary)
        :type bus_spec: dict
        :param atype: Match qemu and atype params
        :type atype: bool
        :return: All matching buses
        :rtype: List of QSparseBus
        """
        buses = []
        for bus in self.__buses:
            if bus.match_bus(bus_spec, type_test):
                buses.append(bus)
        return buses

    def get_first_free_bus(self, bus_spec, addr):
        """
        :param bus_spec: Bus specification (dictionary)
        :param addr: Desired address
        :return: First matching bus with free desired address (the latest
                 added matching bus)
        """
        buses = self.get_buses(bus_spec)
        for bus in buses:
            _ = bus.get_free_slot(addr)
            if _ is not None and _ is not False:
                return bus

    def insert(self, devices, strict_mode=None):
        """
        Inserts devices into this VM representation
        :param devices: List of qdevices.QBaseDevice devices
        :raise DeviceError: On failure. The representation remains unchanged.
        """
        def cleanup():
            """ Remove all added devices (on failure) """
            for device in added:
                self.wash_the_device_out(device)

        if not isinstance(devices, list):
            devices = [devices]

        added = []
        for device in devices:
            try:
                added.extend(self._insert(device, strict_mode))
            except DeviceError, details:
                cleanup()
                raise DeviceError("%s\nError occurred while inserting device %s"
                                  " (%s). Please check the log for details."
                                  % (details, device, devices))
        return added

    def _insert(self, device, strict_mode=None):
        """
        Inserts device into this VM representation
        :param device: qdevices.QBaseDevice device
        :raise DeviceError: On failure. The representation remains unchanged.

        1)  get list of matching parent buses
        2)  try to find matching bus+address
        2b) add bus required additional devices prior to adding this device
        3)  add child buses
        4)  append into self.devices
        """
        def clean(device, added_devices):
            """ Remove all inserted devices (on failure) """
            self.wash_the_device_out(device)
            for device in added_devices:
                self.wash_the_device_out(device)

        if strict_mode is None:
            _strict_mode = self.strict_mode
        if strict_mode is True:
            _strict_mode = True
        else:
            _strict_mode = False
        added_devices = []
        if device.parent_bus is not None and not isinstance(device.parent_bus,
                                                            (list, tuple)):
            # it have to be list of parent buses
            device.parent_bus = (device.parent_bus,)
        for parent_bus in device.parent_bus:
            # type, aobject, busid
            if parent_bus is None:
                continue
            # 1
            buses = self.get_buses(parent_bus, True)
            if not buses:
                err = "ParentBus(%s): No matching bus\n" % parent_bus
                clean(device, added_devices)
                raise DeviceInsertError(device, err, self)
            bus_returns = []
            strict_mode = _strict_mode
            for bus in buses:   # 2
                if not bus.match_bus(parent_bus, False):
                    # First available bus in qemu is not of the same type as
                    # we in autotest require. Force strict mode to get this
                    # device into the correct bus (ide-hd could go into ahci
                    # and ide hba, qemu doesn't care, autotest does).
                    strict_mode = True
                    bus_returns.append(-1)  # Don't use this bus
                    continue
                bus_returns.append(bus.insert(device, strict_mode))
                if isinstance(bus_returns[-1], list):   # we are done
                    # The bus might require additional devices plugged first
                    try:
                        added_devices.extend(self.insert(bus_returns[-1]))
                    except DeviceError, details:
                        err = ("Can't insert device %s because additional "
                               "device required by bus %s failed to be "
                               "inserted with:\n%s" % (device, bus, details))
                        clean(device, added_devices)
                        raise DeviceError(err)
                    break
            if isinstance(bus_returns[-1], list):   # we are done
                continue
            err = "ParentBus(%s): No free matching bus\n" % parent_bus
            clean(device, added_devices)
            raise DeviceInsertError(device, err, self)
        # 3
        for bus in device.child_bus:
            self.__buses.insert(0, bus)
        # 4
        if device.get_qid() and self.get_by_qid(device.get_qid()):
            err = "Devices qid %s already used in VM\n" % device.get_qid()
            clean(device, added_devices)
            raise DeviceInsertError(device, err, self)
        device.set_aid(self.__create_unique_aid(device.get_qid()))
        self.__devices.append(device)
        added_devices.append(device)
        return added_devices

    def simple_hotplug(self, device, monitor):
        """
        Function hotplug device to devices representation. If verification is
        supported by hodplugged device and result of verification is True
        then it calls set_clean. Otherwise it don't call set_clean because
        devices representatio don't know if device is added correctly.

        :param device: Device which should be unplugged.
        :type device: string, qdevices.QDevice.
        :param monitor: Monitor from vm.
        :type monitor: qemu_monitor.Monitor
        :return: tuple(monitor.cmd(), verify_hotplug output)
        """
        self.set_dirty()

        out = device.hotplug(monitor)
        ver_out = device.verify_hotplug(out, monitor)

        if ver_out is False:
            self.set_clean()
            return out, ver_out

        qdev_out = None
        try:
            qdev_out = self.insert(device)
            if not isinstance(qdev_out, list) or len(qdev_out) != 1:
                raise NotImplementedError("This device %s require to hotplug "
                                          "multiple devices %s, which is not "
                                          "supported." % (device, out))
            if ver_out is True:
                self.set_clean()
        except DeviceError, exc:
            self.set_clean()  # qdev remains consistent
            raise DeviceHotplugError(device, 'According to qemu_device: %s'
                                     % exc, self)
        out = device.hotplug(monitor)

        return out, ver_out

    def simple_unplug(self, device, monitor):
        """
        Function unplug device to devices representation. If verification is
        supported by unplugged device and result of verification is True
        then it calls set_clean. Otherwise it don't call set_clean because
        devices representatio don't know if device is added correctly.

        :param device: Device which should be unplugged.
        :type device: string, qdevices.QDevice.
        :param monitor: Monitor from vm.
        :type monitor: qemu_monitor.Monitor
        :return: tuple(monitor.cmd(), verify_unplug output)
        """
        device = self[device]
        self.set_dirty()
        # Remove all devices, which are removed together with this dev
        out = device.unplug(monitor)

        ver_out = device.verify_unplug(out, monitor)

        if ver_out is False:
            self.set_clean()
            return out, ver_out

        try:
            device.unplug_hook()
            self.remove(device, True)
            if ver_out is True:
                self.set_clean()
            elif out is False:
                raise DeviceUnplugError(device, "Device wasn't unplugged in "
                                        "qemu, but it was unplugged in device "
                                        "representation.", self)
        except (DeviceError, KeyError), exc:
            device.unplug_unhook()
            raise DeviceUnplugError(device, exc, self)

        return out, ver_out

    def hotplug_verified(self):
        """
        This function should be used after you verify, that hotplug was
        successful. For each hotplug call, hotplug_verified have to be
        executed in order to mark VM as clear.

        :warning: If you can't verify, that hotplug was successful, don't
                  use this function! You could screw-up following tests.
        """
        self.set_clean()

    def list_missing_named_buses(self, bus_pattern, bus_type, bus_count):
        """
        :param bus_pattern: Bus name pattern with 1x%s for idx or %s is
                            appended in the end. ('mybuses' or 'my%sbus').
        :param bus_type: Type of the bus.
        :param bus_count: Desired number of buses.
        :return: List of buses, which are missing in range(bus_count)
        """
        if "%s" not in bus_pattern:
            bus_pattern = bus_pattern + "%s"
        missing_buses = [bus_pattern % i for i in xrange(bus_count)]
        for bus in self.__buses:
            if bus.type == bus_type and re.match(bus_pattern % '\d+',
                                                 bus.busid):
                if bus.busid in missing_buses:
                    missing_buses.remove(bus.busid)
        return missing_buses

    def idx_of_next_named_bus(self, bus_pattern):
        """
        :param bus_pattern: Bus name prefix without %s and tailing digit
        :return: Name of the next bus (integer is appended and incremented
                 until there is no existing bus).
        """
        if "%s" not in bus_pattern:
            bus_pattern = bus_pattern + "%s"
        buses = []
        for bus in self.__buses:
            if bus.busid and re.match(bus_pattern % '\d+', bus.busid):
                buses.append(bus.busid)
        i = 0
        while True:
            if bus_pattern % i not in buses:
                return i
            i += 1

    def cmdline(self, dynamic=True):
        """
        Creates cmdline arguments for creating all defined devices
        :return: cmdline of all devices (without qemu-cmd itself)
        """
        out = ""
        for device in self.__devices:
            if dynamic:
                _out = device.cmdline()
            else:
                _out = device.cmdline_nd()
            if _out:
                out += " %s" % _out
        if out:
            return out[1:]

    def hook_fill_scsi_hbas(self, params):
        """
        This hook creates dummy scsi hba per 7 -drive 'scsi' devices.
        """
        i = 6   # We are going to divide it by 7 so 6 will result in 0
        for image_name in params.objects("images"):
            _is_oldscsi = (params.object_params(image_name).get('drive_format')
                           == 'scsi')
            _scsi_without_device = (not self.has_option('device') and
                                    params.object_params(image_name)
                                    .get('drive_format', 'virtio_blk')
                                    .startswith('scsi'))
            if _is_oldscsi or _scsi_without_device:
                i += 1

        for image_name in params.objects("cdroms"):
            _is_oldscsi = (params.object_params(image_name).get('cd_format')
                           == 'scsi')
            _scsi_without_device = (not self.has_option('device') and
                                    params.object_params(image_name)
                                    .get('cd_format', 'virtio_blk')
                                    .startswith('scsi'))
            if _is_oldscsi or _scsi_without_device:
                i += 1

        for i in xrange(i / 7):     # Autocreated lsi hba
            if arch.ARCH == 'ppc64':
                _name = 'spapr-vscsi%s' % i
                bus = qbuses.QSCSIBus("scsi.0", 'SCSI', [8, 16384],
                                      atype='spapr-vscsi')
                self.insert(qdevices.QStringDevice(_name,
                                                   parent_bus={'aobject':
                                                               params.get('pci_bus',
                                                                          'pci.0')},
                                                   child_bus=bus))
            else:
                _name = 'lsi53c895a%s' % i
                bus = qbuses.QSCSIBus("scsi.0", 'SCSI', [8, 16384], atype='lsi53c895a')
                self.insert(qdevices.QStringDevice(_name,
                                                   parent_bus={'aobject':
                                                               params.get('pci_bus',
                                                                          'pci.0')},
                                                   child_bus=bus))

    # Machine related methods
    def machine_by_params(self, params=None):
        """
        Choose the used machine and set the default devices accordingly
        :param params: VM params
        :return: List of added devices (including default buses)
        """
        def machine_q35(cmd=False):
            """
            Q35 + ICH9
            :param cmd: If set uses "-M $cmd" to force this machine type
            :return: List of added devices (including default buses)
            """
            logging.warn('Using Q35 machine which is not yet fullytested on '
                         'virt-test. False errors might occur.')
            devices = []
            bus = (qbuses.QPCIBus('pcie.0', 'PCIE', 'pci.0'),
                   qbuses.QStrictCustomBus(None, [['chassis'], [256]], '_PCI_CHASSIS',
                                           first_port=[1]),
                   qbuses.QStrictCustomBus(None, [['chassis_nr'], [256]],
                                           '_PCI_CHASSIS_NR', first_port=[1]))
            devices.append(qdevices.QStringDevice('machine', cmdline=cmd,
                                                  child_bus=bus,
                                                  aobject="pci.0"))
            devices.append(qdevices.QStringDevice('mch', {'addr': 0, 'driver': 'mch'},
                                                  parent_bus={'aobject': 'pci.0'}))
            devices.append(qdevices.QStringDevice('ICH9 LPC', {'addr': '1f.0',
                                                               'driver': 'ICH9 LPC'},
                                                  parent_bus={'aobject': 'pci.0'}))
            devices.append(qdevices.QStringDevice('ICH9 SMB', {'addr': '1f.3',
                                                               'driver': 'ICH9 SMB'},
                                                  parent_bus={'aobject': 'pci.0'}))
            devices.append(qdevices.QStringDevice('ICH9-ahci', {'addr': '1f.2',
                                                                'driver': 'ich9-ahci'},
                                                  parent_bus={'aobject': 'pci.0'},
                                                  child_bus=qbuses.QAHCIBus('ide')))
            if self.has_option('device') and self.has_option("global"):
                devices.append(qdevices.QStringDevice('fdc',
                                                      child_bus=qbuses.QFloppyBus('floppy')))
            else:
                devices.append(qdevices.QStringDevice('fdc',
                                                      child_bus=qbuses.QOldFloppyBus('floppy'))
                               )
            return devices

        def machine_i440FX(cmd=False):
            """
            i440FX + PIIX
            :param cmd: If set uses "-M $cmd" to force this machine type
            :return: List of added devices (including default buses)
            """
            devices = []
            if arch.ARCH == 'ppc64':
                pci_bus = "pci"
            else:
                pci_bus = "pci.0"
            bus = (qbuses.QPCIBus(pci_bus, 'PCI', 'pci.0'),
                   qbuses.QStrictCustomBus(None, [['chassis'], [256]], '_PCI_CHASSIS',
                                           first_port=[1]),
                   qbuses.QStrictCustomBus(None, [['chassis_nr'], [256]],
                                           '_PCI_CHASSIS_NR', first_port=[1]))
            devices.append(qdevices.QStringDevice('machine', cmdline=cmd,
                                                  child_bus=bus,
                                                  aobject="pci.0"))
            devices.append(qdevices.QStringDevice('i440FX',
                                                  {'addr': 0, 'driver': 'i440FX'},
                                                  parent_bus={'aobject': 'pci.0'}))
            devices.append(qdevices.QStringDevice('PIIX4_PM', {'addr': '01.3',
                                                               'driver': 'PIIX4_PM'},
                                                  parent_bus={'aobject': 'pci.0'}))
            devices.append(qdevices.QStringDevice('PIIX3',
                                                  {'addr': 1, 'driver': 'PIIX3'},
                                                  parent_bus={'aobject': 'pci.0'}))
            devices.append(qdevices.QStringDevice('piix3-ide', {'addr': '01.1',
                                                                'driver': 'piix3-ide'},
                                                  parent_bus={'aobject': 'pci.0'},
                                                  child_bus=qbuses.QIDEBus('ide')))
            if self.has_option('device') and self.has_option("global"):
                devices.append(qdevices.QStringDevice('fdc',
                                                      child_bus=qbuses.QFloppyBus('floppy')))
            else:
                devices.append(qdevices.QStringDevice('fdc',
                                                      child_bus=qbuses.QOldFloppyBus('floppy'))
                               )
            return devices

        def machine_other(cmd=False):
            """
            isapc or unknown machine type. This type doesn't add any default
            buses or devices, only sets the cmdline.
            :param cmd: If set uses "-M $cmd" to force this machine type
            :return: List of added devices (including default buses)
            """
            logging.warn('Machine type isa/unknown is not supported by '
                         'virt-test. False errors might occur')
            devices = []
            devices.append(qdevices.QStringDevice('machine', cmdline=cmd))
            return devices

        machine_type = params.get('machine_type')
        if machine_type:
            m_types = []
            for _ in self.__machine_types.splitlines()[1:]:
                m_types.append(_.split()[0])

            if machine_type in m_types:
                if (self.has_option('M') or self.has_option('machine')):
                    cmd = "-M %s" % machine_type
                else:
                    cmd = ""
                if 'q35' in machine_type:   # Q35 + ICH9
                    devices = machine_q35(cmd)
                elif 'isapc' not in machine_type:   # i440FX
                    devices = machine_i440FX(cmd)
                else:   # isapc (or other)
                    devices = machine_other(cmd)
            elif params.get("invalid_machine_type", "no") == "yes":
                # For negative testing pretend the unsupported machine is
                # similar to i440fx one (1 PCI bus, ..)
                devices = machine_i440FX("-M %s" % machine_type)
            else:
                raise error.TestNAError("Unsupported machine type %s." %
                                        (machine_type))
        else:
            devices = None
            for _ in self.__machine_types.splitlines()[1:]:
                if 'default' in _:
                    if 'q35' in machine_type:   # Q35 + ICH9
                        devices = machine_q35(False)
                    elif 'isapc' not in machine_type:   # i440FX
                        devices = machine_i440FX(False)
                    else:   # isapc (or other)
                        logging.warn('Machine isa/unknown is not supported by '
                                     'virt-test. False errors might occur')
                        devices = machine_other(False)
            if not devices:
                logging.warn('Unable to find the default machine type, using '
                             'i440FX')
                devices = machine_i440FX(False)

        # reserve pci.0 addresses
        pci_params = params.object_params('pci.0')
        reserved = pci_params.get('reserved_slots', '').split()
        if reserved:
            for bus in self.__buses:
                if bus.aobject == "pci.0":
                    for addr in reserved:
                        bus.reserve(hex(int(addr)))
                    break
        return devices

    # USB Controller related methods
    def usbc_by_variables(self, usb_id, usb_type, multifunction=False,
                          masterbus=None, firstport=None, freq=None,
                          max_ports=6, pci_addr=None, pci_bus='pci.0'):
        """
        Creates usb-controller devices by variables
        :param usb_id: Usb bus name
        :param usb_type: Usb bus type
        :param multifunction: Is the bus multifunction
        :param masterbus: Is this bus master?
        :param firstport: Offset of the first port
        :param freq: Bus frequency
        :param max_ports: How many ports this bus have [6]
        :param pci_addr: Desired PCI address
        :return: List of QDev devices
        """
        if not self.has_option("device"):
            # Okay, for the archaic qemu which has not device parameter,
            # just return a usb uhci controller.
            # If choose this kind of usb controller, it has no name/id,
            # and only can be created once, so give it a special name.
            usb = qdevices.QStringDevice("oldusb", cmdline="-usb",
                                         child_bus=qbuses.QUSBBus(2, 'usb.0', 'uhci', usb_id))
            return [usb]

        if not self.has_device(usb_type):
            raise error.TestNAError("usb controller %s not available"
                                    % usb_type)

        usb = qdevices.QDevice(usb_type, {}, usb_id, {'aobject': pci_bus},
                               qbuses.QUSBBus(max_ports, '%s.0' % usb_id, usb_type, usb_id))
        new_usbs = [usb]    # each usb dev might compound of multiple devs
        # TODO: Add 'bus' property (it was not in the original version)
        usb.set_param('id', usb_id)
        usb.set_param('masterbus', masterbus)
        usb.set_param('multifunction', multifunction)
        usb.set_param('firstport', firstport)
        usb.set_param('freq', freq)
        usb.set_param('addr', pci_addr)

        if usb_type == "ich9-usb-ehci1":
            usb.set_param('addr', '1d.7')
            usb.set_param('multifunction', 'on')
            for i in xrange(3):
                new_usbs.append(qdevices.QDevice('ich9-usb-uhci%d' % (i + 1), {},
                                                 usb_id))
                new_usbs[-1].parent_bus = {'aobject': pci_bus}
                new_usbs[-1].set_param('id', '%s.%d' % (usb_id, i))
                new_usbs[-1].set_param('multifunction', 'on')
                new_usbs[-1].set_param('masterbus', '%s.0' % usb_id)
                # current qdevices doesn't support x.y addr. Plug only
                # the 0th one into this representation.
                new_usbs[-1].set_param('addr', '1d.%d' % (2 * i))
                new_usbs[-1].set_param('firstport', 2 * i)
        return new_usbs

    def usbc_by_params(self, usb_name, params):
        """
        Wrapper for creating usb bus from autotest usb params.
        :param usb_name: Name of the usb bus
        :param params: USB params (params.object_params(usb_name))
        :return: List of QDev devices
        """
        return self.usbc_by_variables(usb_name,
                                      params.get('usb_type'),
                                      params.get('multifunction'),
                                      params.get('masterbus'),
                                      params.get('firstport'),
                                      params.get('freq'),
                                      params.get('max_ports', 6),
                                      params.get('pci_addr'),
                                      params.get('pci_bus', 'pci.0'))

    # USB Device related methods
    def usb_by_variables(self, usb_name, usb_type, controller_type, bus=None,
                         port=None):
        """
        Creates usb-devices by variables.
        :param usb_name: usb name
        :param usb_type: usb type (usb-tablet, usb-serial, ...)
        :param controller_type: type of the controller (uhci, ehci, xhci, ...)
        :param bus: the bus name (my_bus.0, ...)
        :param port: port specifiacation (4, 4.1.2, ...)
        :return: QDev device
        """
        if not self.has_device(usb_type):
            raise error.TestNAError("usb device %s not available"
                                    % usb_type)
        if self.has_option('device'):
            device = qdevices.QDevice(usb_type, aobject=usb_name)
            device.set_param('id', 'usb-%s' % usb_name)
            device.set_param('bus', bus)
            device.set_param('port', port)
            device.parent_bus += ({'type': controller_type},)
        else:
            if "tablet" in usb_type:
                device = qdevices.QStringDevice('usb-%s' % usb_name,
                                                cmdline='-usbdevice %s' % usb_name)
            else:
                device = qdevices.QStringDevice('missing-usb-%s' % usb_name)
                logging.error("This qemu supports only tablet device; ignoring"
                              " %s", usb_name)
        return device

    def usb_by_params(self, usb_name, params):
        """
        Wrapper for creating usb devices from autotest params.
        :param usb_name: Name of the usb
        :param params: USB device's params
        :return: QDev device
        """
        return self.usb_by_variables(usb_name,
                                     params.get("usb_type"),
                                     params.get("usb_controller"),
                                     params.get("bus"),
                                     params.get("port"))

    # Images (disk, cdrom, floppy) device related methods
    def images_define_by_variables(self, name, filename, index=None, fmt=None,
                                   cache=None, werror=None, rerror=None, serial=None,
                                   snapshot=None, boot=None, blkdebug=None, bus=None,
                                   unit=None, port=None, bootindex=None, removable=None,
                                   min_io_size=None, opt_io_size=None,
                                   physical_block_size=None, logical_block_size=None,
                                   readonly=None, scsiid=None, lun=None, aio=None,
                                   strict_mode=None, media=None, imgfmt=None,
                                   pci_addr=None, scsi_hba=None, x_data_plane=None,
                                   blk_extra_params=None, scsi=None,
                                   pci_bus='pci.0', drv_extra_params=None):
        """
        Creates related devices by variables
        :note: To skip the argument use None, to disable it use False
        :note: Strictly bool options accept "yes", "on" and True ("no"...)
        :param name: Autotest name of this disk
        :param filename: Path to the disk file
        :param index: drive index (used for generating names)
        :param fmt: drive subsystem type (ide, scsi, virtio, usb2, ...)
        :param cache: disk cache (none, writethrough, writeback)
        :param werror: What to do when write error occurs (stop, ...)
        :param rerror: What to do when read error occurs (stop, ...)
        :param serial: drive serial number ($string)
        :param snapshot: use snapshot? ($bool)
        :param boot: is bootable? ($bool)
        :param blkdebug: use blkdebug (None, blkdebug_filename)
        :param bus: 1st level of disk location (index of bus) ($int)
        :param unit: 2nd level of disk location (unit/scsiid/...) ($int)
        :param port: 3rd level of disk location (port/lun/...) ($int)
        :param bootindex: device boot priority ($int)
        :param removable: can the drive be removed? ($bool)
        :param min_io_size: Min allowed io size
        :param opt_io_size: Optimal io size
        :param physical_block_size: set physical_block_size ($int)
        :param logical_block_size: set logical_block_size ($int)
        :param readonly: set the drive readonly ($bool)
        :param scsiid: Deprecated 2nd level of disk location (&unit)
        :param lun: Deprecated 3rd level of disk location (&port)
        :param aio: set the type of async IO (native, threads, ..)
        :param strict_mode: enforce optional parameters (address, ...) ($bool)
        :param media: type of the media (disk, cdrom, ...)
        :param imgfmt: image format (qcow2, raw, ...)
        :param pci_addr: drive pci address ($int)
        :param scsi_hba: Custom scsi HBA
        """
        def define_hbas(qtype, atype, bus, unit, port, qbus, addr_spec=None,
                        pci_bus='pci.0'):
            """
            Helper for creating HBAs of certain type.
            """
            devices = []
            if qbus == qbuses.QAHCIBus:    # AHCI uses multiple ports, id is different
                _hba = 'ahci%s'
            else:
                _hba = atype.replace('-', '_') + '%s.0'  # HBA id
            _bus = bus
            if bus is None:
                bus = self.get_first_free_bus({'type': qtype, 'atype': atype},
                                              [unit, port])
                if bus is None:
                    bus = self.idx_of_next_named_bus(_hba)
                else:
                    bus = bus.busid
            if isinstance(bus, int):
                for bus_name in self.list_missing_named_buses(
                        _hba, qtype, bus + 1):
                    _bus_name = bus_name.rsplit('.')[0]
                    if addr_spec:
                        dev = qdevices.QDevice(params={'id': _bus_name,
                                                       'driver': atype},
                                               parent_bus={'aobject': pci_bus},
                                               child_bus=qbus(busid=bus_name,
                                                              bus_type=qtype,
                                                              addr_spec=addr_spec,
                                                              atype=atype))
                    else:
                        dev = qdevices.QDevice(params={'id': _bus_name,
                                                       'driver': atype},
                                               parent_bus={'aobject': pci_bus},
                                               child_bus=qbus(busid=bus_name))
                    devices.append(dev)
                bus = _hba % bus
            if qbus == qbuses.QAHCIBus and unit is not None:
                bus += ".%d" % unit
            elif _bus is None:    # If bus was not set, don't set it
                bus = None
            return devices, bus, {'type': qtype, 'atype': atype}

        #
        # Parse params
        #
        devices = []    # All related devices

        use_device = self.has_option("device")
        if fmt == "scsi":   # fmt=scsi force the old version of devices
            logging.warn("'scsi' drive_format is deprecated, please use the "
                         "new lsi_scsi type for disk %s", name)
            use_device = False
        if not fmt:
            use_device = False
        if fmt == 'floppy' and not self.has_option("global"):
            use_device = False

        if strict_mode is None:
            strict_mode = self.strict_mode
        if strict_mode:     # Force default variables
            if cache is None:
                cache = "none"
            if removable is None:
                removable = "yes"
            if aio is None:
                aio = "native"
            if media is None:
                media = "disk"
        else:       # Skip default variables
            imgfmt = None
            if media != 'cdrom':    # ignore only 'disk'
                media = None

        if "[,boot=on|off]" not in self.get_help_text():
            if boot in ('yes', 'on', True):
                bootindex = "1"
            boot = None

        bus = none_or_int(bus)     # First level
        unit = none_or_int(unit)   # Second level
        port = none_or_int(port)   # Third level
        # Compatibility with old params - scsiid, lun
        if scsiid is not None:
            logging.warn("drive_scsiid param is obsolete, use drive_unit "
                         "instead (disk %s)", name)
            unit = none_or_int(scsiid)
        if lun is not None:
            logging.warn("drive_lun param is obsolete, use drive_port instead "
                         "(disk %s)", name)
            port = none_or_int(lun)
        if pci_addr is not None and fmt == 'virtio':
            logging.warn("drive_pci_addr is obsolete, use drive_bus instead "
                         "(disk %s)", name)
            bus = none_or_int(pci_addr)

        #
        # HBA
        # fmt: ide, scsi, virtio, scsi-hd, ahci, usb1,2,3 + hba
        # device: ide-drive, usb-storage, scsi-hd, scsi-cd, virtio-blk-pci
        # bus: ahci, virtio-scsi-pci, USB
        #
        if not use_device:
            if fmt and (fmt == "scsi" or (fmt.startswith('scsi') and
                                          (scsi_hba == 'lsi53c895a' or
                                           scsi_hba == 'spapr-vscsi'))):
                if not (bus is None and unit is None and port is None):
                    logging.warn("Using scsi interface without -device "
                                 "support; ignoring bus/unit/port. (%s)", name)
                    bus, unit, port = None, None, None
                # In case we hotplug, lsi wasn't added during the startup hook
                if arch.ARCH == 'ppc64':
                    _ = define_hbas('SCSI', 'spapr-vscsi', None, None, None,
                                    qbuses.QSCSIBus, [8, 16384])
                else:
                    _ = define_hbas('SCSI', 'lsi53c895a', None, None, None,
                                    qbuses.QSCSIBus, [8, 16384])
                devices.extend(_[0])
        elif fmt == "ide":
            if bus:
                logging.warn('ide supports only 1 hba, use drive_unit to set'
                             'ide.* for disk %s', name)
            bus = unit
            dev_parent = {'type': 'IDE', 'atype': 'ide'}
        elif fmt == "ahci":
            devs, bus, dev_parent = define_hbas('IDE', 'ahci', bus, unit, port,
                                                qbuses.QAHCIBus)
            devices.extend(devs)
        elif fmt.startswith('scsi-'):
            if not scsi_hba:
                scsi_hba = "virtio-scsi-pci"
            addr_spec = None
            if scsi_hba == 'lsi53c895a' or scsi_hba == 'spapr-vscsi':
                addr_spec = [8, 16384]
            elif scsi_hba == 'virtio-scsi-pci':
                addr_spec = [256, 16384]
            _, bus, dev_parent = define_hbas('SCSI', scsi_hba, bus, unit, port,
                                             qbuses.QSCSIBus, addr_spec)
            devices.extend(_)
        elif fmt in ('usb1', 'usb2', 'usb3'):
            if bus:
                logging.warn('Manual setting of drive_bus is not yet supported'
                             ' for usb disk %s', name)
                bus = None
            if fmt == 'usb1':
                dev_parent = {'type': 'uhci'}
            elif fmt == 'usb2':
                dev_parent = {'type': 'ehci'}
            elif fmt == 'usb3':
                dev_parent = {'type': 'xhci'}
        elif fmt == 'virtio':
            dev_parent = {'aobject': pci_bus}
        else:
            dev_parent = {'type': fmt}

        #
        # Drive
        # -drive fmt or -drive fmt=none -device ...
        #
        if self.has_hmp_cmd('__com.redhat_drive_add') and use_device:
            devices.append(qdevices.QRHDrive(name))
        elif self.has_hmp_cmd('drive_add') and use_device:
            devices.append(qdevices.QHPDrive(name))
        elif self.has_option("device"):
            devices.append(qdevices.QDrive(name, use_device))
        else:       # very old qemu without 'addr' support
            devices.append(qdevices.QOldDrive(name, use_device))
        devices[-1].set_param('if', 'none')
        devices[-1].set_param('cache', cache)
        devices[-1].set_param('rerror', rerror)
        devices[-1].set_param('werror', werror)
        devices[-1].set_param('serial', serial)
        devices[-1].set_param('boot', boot, bool)
        devices[-1].set_param('snapshot', snapshot, bool)
        devices[-1].set_param('readonly', readonly, bool)
        if 'aio' in self.get_help_text():
            devices[-1].set_param('aio', aio)
        devices[-1].set_param('media', media)
        devices[-1].set_param('format', imgfmt)
        if blkdebug is not None:
            devices[-1].set_param('file', 'blkdebug:%s:%s' % (blkdebug,
                                                              filename))
        else:
            devices[-1].set_param('file', filename)
        if drv_extra_params:
            drv_extra_params = (_.split('=', 1) for _ in
                                drv_extra_params.split(',') if _)
            for key, value in drv_extra_params:
                devices[-1].set_param(key, value)
        if not use_device:
            if fmt and fmt.startswith('scsi-'):
                if scsi_hba == 'lsi53c895a' or scsi_hba == 'spapr-vscsi':
                    fmt = 'scsi'  # Compatibility with the new scsi
            if fmt and fmt not in ('ide', 'scsi', 'sd', 'mtd', 'floppy',
                                   'pflash', 'virtio'):
                raise virt_vm.VMDeviceNotSupportedError(self.vmname,
                                                        fmt)
            devices[-1].set_param('if', fmt)    # overwrite previously set None
            if not fmt:     # When fmt unspecified qemu uses ide
                fmt = 'ide'
            devices[-1].set_param('index', index)
            if fmt == 'ide':
                devices[-1].parent_bus = ({'type': fmt.upper(), 'atype': fmt},)
            elif fmt == 'scsi':
                if arch.ARCH == 'ppc64':
                    devices[-1].parent_bus = ({'atype': 'spapr-vscsi',
                                               'type': 'SCSI'},)
                else:
                    devices[-1].parent_bus = ({'atype': 'lsi53c895a',
                                               'type': 'SCSI'},)
            elif fmt == 'floppy':
                devices[-1].parent_bus = ({'type': fmt},)
            elif fmt == 'virtio':
                devices[-1].set_param('addr', pci_addr)
                devices[-1].parent_bus = ({'aobject': pci_bus},)
            if not media == 'cdrom':
                logging.warn("Using -drive fmt=xxx for %s is unsupported "
                             "method, false errors might occur.", name)
            return devices

        #
        # Device
        #
        devices.append(qdevices.QDevice(params={}, aobject=name))
        devices[-1].parent_bus += ({'busid': 'drive_%s' % name}, dev_parent)
        if fmt in ("ide", "ahci"):
            if not self.has_device('ide-hd'):
                devices[-1].set_param('driver', 'ide-drive')
            elif media == 'cdrom':
                devices[-1].set_param('driver', 'ide-cd')
            else:
                devices[-1].set_param('driver', 'ide-hd')
            devices[-1].set_param('unit', port)
        elif fmt and fmt.startswith('scsi-'):
            devices[-1].set_param('driver', fmt)
            devices[-1].set_param('scsi-id', unit)
            devices[-1].set_param('lun', port)
            devices[-1].set_param('removable', removable, bool)
            if strict_mode:
                devices[-1].set_param('channel', 0)
        elif fmt == 'virtio':
            devices[-1].set_param('driver', 'virtio-blk-pci')
            devices[-1].set_param("scsi", scsi, bool)
            if bus is not None:
                devices[-1].set_param('addr', hex(bus))
                bus = None
        elif fmt in ('usb1', 'usb2', 'usb3'):
            devices[-1].set_param('driver', 'usb-storage')
            devices[-1].set_param('port', unit)
            devices[-1].set_param('removable', removable, bool)
        elif fmt == 'floppy':
            # Overwrite qdevices.QDevice with qdevices.QFloppy
            devices[-1] = qdevices.QFloppy(unit, 'drive_%s' % name, name,
                                           ({'busid': 'drive_%s' % name}, {'type': fmt}))
        else:
            logging.warn('Using default device handling (disk %s)', name)
            devices[-1].set_param('driver', fmt)
        # Get the supported options
        options = self.execute_qemu("-device %s,?" % devices[-1]['driver'])
        devices[-1].set_param('id', name)
        devices[-1].set_param('bus', bus)
        devices[-1].set_param('drive', 'drive_%s' % name)
        devices[-1].set_param('logical_block_size', logical_block_size)
        devices[-1].set_param('physical_block_size', physical_block_size)
        devices[-1].set_param('min_io_size', min_io_size)
        devices[-1].set_param('opt_io_size', opt_io_size)
        devices[-1].set_param('bootindex', bootindex)
        devices[-1].set_param('x-data-plane', x_data_plane, bool)
        if 'serial' in options:
            devices[-1].set_param('serial', serial)
            devices[-2].set_param('serial', None)   # remove serial from drive
        if blk_extra_params:
            blk_extra_params = (_.split('=', 1) for _ in
                                blk_extra_params.split(',') if _)
            for key, value in blk_extra_params:
                devices[-1].set_param(key, value)

        return devices

    def images_define_by_params(self, name, image_params, media=None,
                                index=None, image_boot=None,
                                image_bootindex=None):
        """
        Wrapper for creating disks and related hbas from autotest image params.

        :note: To skip the argument use None, to disable it use False
        :note: Strictly bool options accept "yes", "on" and True ("no"...)
        :note: Options starting with '_' are optional and used only when
               strict_mode is True
        :param name: Name of the new disk
        :param params: Disk params (params.object_params(name))
        """
        shared_dir = os.path.join(data_dir.get_data_dir(), "shared")
        return self.images_define_by_variables(name,
                                               storage.get_image_filename(
                                                   image_params,
                                                   data_dir.get_data_dir()),
                                               index,
                                               image_params.get(
                                                   "drive_format"),
                                               image_params.get("drive_cache"),
                                               image_params.get(
                                                   "drive_werror"),
                                               image_params.get(
                                                   "drive_rerror"),
                                               image_params.get(
                                                   "drive_serial"),
                                               image_params.get(
                                                   "image_snapshot"),
                                               image_boot,
                                               storage.get_image_blkdebug_filename(
                                                   image_params,
                                                   shared_dir),
                                               image_params.get("drive_bus"),
                                               image_params.get("drive_unit"),
                                               image_params.get("drive_port"),
                                               image_bootindex,
                                               image_params.get("removable"),
                                               image_params.get("min_io_size"),
                                               image_params.get("opt_io_size"),
                                               image_params.get(
                                                   "physical_block_size"),
                                               image_params.get(
                                                   "logical_block_size"),
                                               image_params.get(
                                                   "image_readonly"),
                                               image_params.get(
                                                   "drive_scsiid"),
                                               image_params.get("drive_lun"),
                                               image_params.get("image_aio"),
                                               image_params.get(
                                                   "strict_mode") == "yes",
                                               media,
                                               image_params.get(
                                                   "image_format"),
                                               image_params.get(
                                                   "drive_pci_addr"),
                                               image_params.get("scsi_hba"),
                                               image_params.get(
                                                   "x-data-plane"),
                                               image_params.get(
                                                   "blk_extra_params"),
                                               image_params.get("virtio-blk-pci_scsi"),
                                               image_params.get('pci_bus', 'pci.0'),
                                               image_params.get("drv_extra_params"))

    def cdroms_define_by_params(self, name, image_params, media=None,
                                index=None, image_boot=None,
                                image_bootindex=None):
        """
        Wrapper for creating cdrom and related hbas from autotest image params.

        :note: To skip the argument use None, to disable it use False
        :note: Strictly bool options accept "yes", "on" and True ("no"...)
        :note: Options starting with '_' are optional and used only when
               strict_mode is True
        :param name: Name of the new disk
        :param params: Disk params (params.object_params(name))
        """
        iso = image_params.get('cdrom')
        image_params['image_name'] = ""
        if iso:
            image_params['image_name'] = os.path.join(data_dir.get_data_dir(),
                                                      image_params.get('cdrom')
                                                      )
        image_params['image_raw_device'] = 'yes'
        cd_format = image_params.get('cd_format')
        if cd_format is None or cd_format is 'ide':
            if not self.get_buses({'atype': 'ide'}):
                logging.warn("cd_format IDE not available, using AHCI "
                             "instead.")
                cd_format = 'ahci'
        shared_dir = os.path.join(data_dir.get_data_dir(), "shared")
        return self.images_define_by_variables(name,
                                               storage.get_image_filename(
                                                   image_params,
                                                   data_dir.get_data_dir()),
                                               index,
                                               cd_format,
                                               '',     # skip drive_cache
                                               image_params.get(
                                                   "drive_werror"),
                                               image_params.get(
                                                   "drive_rerror"),
                                               image_params.get(
                                                   "drive_serial"),
                                               image_params.get(
                                                   "image_snapshot"),
                                               image_boot,
                                               storage.get_image_blkdebug_filename(
                                                   image_params,
                                                   shared_dir),
                                               image_params.get("drive_bus"),
                                               image_params.get("drive_unit"),
                                               image_params.get("drive_port"),
                                               image_bootindex,
                                               image_params.get("removable"),
                                               image_params.get("min_io_size"),
                                               image_params.get("opt_io_size"),
                                               image_params.get(
                                                   "physical_block_size"),
                                               image_params.get(
                                                   "logical_block_size"),
                                               image_params.get(
                                                   "image_readonly"),
                                               image_params.get(
                                                   "drive_scsiid"),
                                               image_params.get("drive_lun"),
                                               image_params.get("image_aio"),
                                               image_params.get(
                                                   "strict_mode") == "yes",
                                               media,
                                               None,     # skip img_fmt
                                               image_params.get(
                                                   "drive_pci_addr"),
                                               image_params.get("scsi_hba"),
                                               image_params.get(
                                                   "x-data-plane"),
                                               image_params.get(
                                                   "blk_extra_params"),
                                               image_params.get("virtio-blk-pci_scsi"),
                                               image_params.get('pci_bus', 'pci.0'),
                                               image_params.get("drv_extra_params"))

    def pcic_by_params(self, name, params):
        """
        Creates pci controller/switch/... based on params

        :param name: Autotest name
        :param params: PCI controller params
        :note: x3130 creates x3130-upstream bus + xio3130-downstream port for
               each inserted device.
        :warning: x3130-upstream device creates only x3130-upstream device
                  and you are responsible for creating the downstream ports.
        """
        driver = params.get('type', 'ioh3420')
        if driver in ('ioh3420', 'x3130-upstream', 'x3130'):
            bus_type = 'PCIE'
        else:
            bus_type = 'PCI'
        parent_bus = [{'aobject': params.get('pci_bus', 'pci.0')}]
        if driver == 'x3130':
            bus = qbuses.QPCISwitchBus(name, bus_type, 'xio3130-downstream', name)
            driver = 'x3130-upstream'
        else:
            if driver == 'pci-bridge':  # addr 1-19, chasis_nr
                parent_bus.append({'busid': '_PCI_CHASSIS_NR'})
                bus_length = 20
                bus_first_port = 1
            elif driver == 'i82801b11-bridge':  # addr 1-19
                bus_length = 20
                bus_first_port = 1
            else:   # addr = 0-31
                bus_length = 32
                bus_first_port = 0
            bus = qbuses.QPCIBus(name, bus_type, name, bus_length, bus_first_port)
        for addr in params.get('reserved_slots', '').split():
            bus.reserve(addr)
        return qdevices.QDevice(driver, {'id': name}, aobject=name,
                                parent_bus=parent_bus,
                                child_bus=bus)
