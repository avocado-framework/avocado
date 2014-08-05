"""
Autotest representations of qemu buses.

These classes emulates the usual qemu buses behaviors in order to create
or match the autotest params into qemu qdev structure.

:copyright: 2012-2013 Red Hat Inc.
"""
# Autotest imports
import qdevices
from utils import none_or_int


#
# Bus representations
# HDA, I2C, IDE, ISA, PCI, SCSI, System, uhci, ehci, ohci, xhci, ccid,
# virtio-serial-bus
#
class QSparseBus(object):

    """
    Universal bus representation object.

    It creates an abstraction of the way how buses works in qemu. Additionally
    it can store incorrect records (out-of-range addr, multiple devs, ...).
    Everything with bad* prefix means it concerns the bad records (badbus).

    You can insert and remove device to certain address, address ranges or let
    the bus assign first free address. The order of addr_spec does matter since
    the last item is incremented first.

    There are 3 different address representation used:

    stor_addr
        stored address representation '$first-$second-...-$ZZZ'
    addr
        internal address representation [$first, $second, ..., $ZZZ]
    device_addr
        qemu address stored into separate device params (bus, port)
        device{$param1:$first, $param2:$second, ..., $paramZZZ, $ZZZ}

    :note: When you insert a device, it's properties might be updated (addr,..)
    """

    def __init__(self, bus_item, addr_spec, busid, bus_type=None, aobject=None,
                 atype=None):
        """
        :param bus_item: Name of the parameter which specifies bus (bus)
        :type bus_item: str
        :param addr_spec: Bus address specification [names][lengths]
        :type addr_spec: list of lists
        :param busid: id of the bus (pci.0)
        :type busid: str
        :param bus_type: type of the bus (pci)
        :type bus_type: dict
        :param aobject: Related autotest object (image1)
        :type aobject: str
        :param atype: Autotest bus type
        :type atype: str
        """
        self.busid = busid
        self.type = bus_type
        self.aobject = aobject
        self.bus = {}                       # Normal bus records
        self.bus_item = bus_item            # bus param name
        self.addr_items = addr_spec[0]      # [names][lengths]
        self.addr_lengths = addr_spec[1]
        self.atype = atype
        self.__device = None
        self.first_port = [0] * len(addr_spec[0])

    def __str__(self):
        """ default string representation """
        return self.str_short()

    def __getitem__(self, item):
        """
        :param item: autotest id or QObject-like object
        :return: First matching object from this bus
        :raise KeyError: In case no match was found
        """
        if isinstance(item, qdevices.QBaseDevice):
            if item in self.bus.itervalues():
                return item
        else:
            for device in self.bus.itervalues():
                if device.get_aid() == item:
                    return device
        raise KeyError("Device %s is not in %s" % (item, self))

    def get(self, item):
        """
        :param item: autotest id or QObject-like object
        :return: First matching object from this bus or None
        """
        if item in self:
            return self[item]

    def __delitem__(self, item):
        """
        Remove device from bus
        :param item: autotest id or QObject-like object
        :raise KeyError: In case no match was found
        """
        self.remove(self[item])

    def __len__(self):
        """ :return: Number of devices in this bus """
        return len(self.bus)

    def __contains__(self, item):
        """
        Is specified item in this bus?
        :param item: autotest id or QObject-like object
        :return: True - yes, False - no
        """
        if isinstance(item, qdevices.QBaseDevice):
            if item in self.bus.itervalues():
                return True
        else:
            for device in self:
                if device.get_aid() == item:
                    return True
        return False

    def __iter__(self):
        """ Iterate over all defined devices. """
        return self.bus.itervalues()

    def str_short(self):
        """ short string representation """
        if self.atype:
            bus_type = self.atype
        else:
            bus_type = self.type
        return "%s(%s): %s" % (self.busid, bus_type, self._str_devices())

    def _str_devices(self):
        """ short string representation of the good bus """
        out = '{'
        for addr in sorted(self.bus.keys()):
            out += "%s:%s," % (addr, self.bus[addr])
        if out[-1] == ',':
            out = out[:-1]
        return out + '}'

    def str_long(self):
        """ long string representation """
        if self.atype:
            bus_type = self.atype
        else:
            bus_type = self.type
        return "Bus %s, type=%s\nSlots:\n%s" % (self.busid, bus_type,
                                                self._str_devices_long())

    def _str_devices_long(self):
        """ long string representation of devices in the good bus """
        out = ""
        for addr, dev in self.bus.iteritems():
            out += '%s< %4s >%s\n  ' % ('-' * 15, addr,
                                        '-' * 15)
            if isinstance(dev, str):
                out += '"%s"\n  ' % dev
            else:
                out += dev.str_long().replace('\n', '\n  ')
                out = out[:-3]
            out += '\n'
        return out

    def _increment_addr(self, addr, last_addr=None):
        """
        Increment addr base of addr_pattern and last used addr
        :param addr: addr_pattern
        :param last_addr: previous address
        :return: last_addr + 1
        """
        if not last_addr:
            last_addr = [0] * len(self.addr_lengths)
        i = -1
        while True:
            if i < -len(self.addr_lengths):
                return False
            if addr[i] is not None:
                i -= 1
                continue
            last_addr[i] += 1
            if last_addr[i] < self.addr_lengths[i]:
                return last_addr
            last_addr[i] = 0
            i -= 1

    @staticmethod
    def _addr2stor(addr):
        """
        Converts internal addr to storable/hashable address
        :param addr: internal address [addr1, addr2, ...]
        :return: storable address "addr1-addr2-..."
        """
        out = ""
        for value in addr:
            if value is None:
                out += '*-'
            else:
                out += '%s-' % value
        if out:
            return out[:-1]
        else:
            return "*"

    def _dev2addr(self, device):
        """
        Parse the internal address out of the device
        :param device: qdevices.QBaseDevice device
        :return: internal address  [addr1, addr2, ...]
        """
        addr = []
        for key in self.addr_items:
            addr.append(none_or_int(device.get_param(key)))
        return addr

    def _set_first_addr(self, addr_pattern):
        """
        :param addr_pattern: Address pattern (full qualified or with Nones)
        :return: first valid address based on addr_pattern
        """
        use_reserved = True
        if addr_pattern is None:
            addr_pattern = [None] * len(self.addr_lengths)
        # set first usable addr
        last_addr = addr_pattern[:]
        if None in last_addr:  # Address is not fully specified
            use_reserved = False    # Use only free address
            for i in xrange(len(last_addr)):
                if last_addr[i] is None:
                    last_addr[i] = self.first_port[i]
        return last_addr, use_reserved

    def get_free_slot(self, addr_pattern):
        """
        Finds unoccupied address

        :param addr_pattern: Address pattern (full qualified or with Nones)
        :return: First free address when found, (free or reserved for this dev)
                 None when no free address is found, (all occupied)
                 False in case of incorrect address (oor)
        """
        # init
        last_addr, use_reserved = self._set_first_addr(addr_pattern)
        # Check the addr_pattern ranges
        for i in xrange(len(self.addr_lengths)):
            if (last_addr[i] < self.first_port[i] or
                    last_addr[i] >= self.addr_lengths[i]):
                return False
        # Increment addr until free match is found
        while last_addr is not False:
            if self._addr2stor(last_addr) not in self.bus:
                return last_addr
            if (use_reserved and
                    self.bus[self._addr2stor(last_addr)] == "reserved"):
                return last_addr
            last_addr = self._increment_addr(addr_pattern, last_addr)
        return None     # No free matching address found

    def _check_bus(self, device):
        """
        Check, whether this device can be plugged into this bus.
        :param device: qdevices.QBaseDevice device
        :return: True in case ids are correct, False when not
        """
        if (device.get_param(self.bus_item) and
                device.get_param(self.bus_item) != self.busid):
            return False
        else:
            return True

    def _set_device_props(self, device, addr):
        """
        Set the full device address
        :param device: qdevices.QBaseDevice device
        :param addr: internal address  [addr1, addr2, ...]
        """
        if self.bus_item:
            device.set_param(self.bus_item, self.busid)
        for i in xrange(len(self.addr_items)):
            device.set_param(self.addr_items[i], addr[i])

    def _update_device_props(self, device, addr):
        """
        Update values of previously set address items.
        :param device: qdevices.QBaseDevice device
        :param addr: internal address  [addr1, addr2, ...]
        """
        if device.get_param(self.bus_item) is not None:
            device.set_param(self.bus_item, self.busid)
        for i in xrange(len(self.addr_items)):
            if device.get_param(self.addr_items[i]) is not None:
                device.set_param(self.addr_items[i], addr[i])

    def reserve(self, addr):
        """
        Reserve the slot
        :param addr: Desired address
        :type addr: internal [addr1, addr2, ..] or stor format "addr1-addr2-.."
        """
        if not isinstance(addr, str):
            addr = self._addr2stor(addr)
        self.bus[addr] = "reserved"

    def insert(self, device, strict_mode=False):
        """
        Insert device into this bus representation.

        :param device: qdevices.QBaseDevice device
        :param strict_mode: Use strict mode (set optional params)
        :return: list of added devices on success,
                 string indicating the failure on failure.
        """
        additional_devices = []
        if not self._check_bus(device):
            return "BusId"
        try:
            addr_pattern = self._dev2addr(device)
        except (ValueError, LookupError):
            return "BasicAddress"
        addr = self.get_free_slot(addr_pattern)
        if addr is None:
            if None in addr_pattern:
                return "NoFreeSlot"
            else:
                return "UsedSlot"
        elif addr is False:
            return "BadAddr(%s)" % addr
        else:
            additional_devices.extend(self._insert(device,
                                                   self._addr2stor(addr)))
        if strict_mode:     # Set full address in strict_mode
            self._set_device_props(device, addr)
        else:
            self._update_device_props(device, addr)
        return additional_devices

    def _insert(self, device, addr):
        """
        Insert device into good bus
        :param device: qdevices.QBaseDevice device
        :param addr: internal address  [addr1, addr2, ...]
        :return: List of additional devices
        """
        self.bus[addr] = device
        return []

    def remove(self, device):
        """
        Remove device from this bus
        :param device: qdevices.QBaseDevice device
        :return: True when removed, False when the device wasn't found
        """
        if device in self.bus.itervalues():
            remove = None
            for key, item in self.bus.iteritems():
                if item is device:
                    remove = key
                    break
            if remove is not None:
                del(self.bus[remove])
                return True
        return False

    def set_device(self, device):
        """ Set the device in which this bus belongs """
        self.__device = device

    def get_device(self):
        """ Get device in which this bus is present """
        return self.__device

    def match_bus(self, bus_spec, type_test=True):
        """
        Check if the bus matches the bus_specification.
        :param bus_spec: Bus specification
        :type bus_spec: dict
        :param type_test: Match only type
        :type type_test: bool
        :return: True when the bus matches the specification
        :rtype: bool
        """
        if type_test and bus_spec.get('type'):
            if isinstance(bus_spec['type'], (tuple, list)):
                for bus_type in bus_spec['type']:
                    if bus_type == self.type:
                        return True
                return False
            elif self.type == bus_spec['type']:
                return True
        for key, value in bus_spec.iteritems():
            if isinstance(value, (tuple, list)):
                for val in value:
                    if self.__dict__.get(key, None) == val:
                        break
                else:
                    return False
            elif self.__dict__.get(key, None) != value:
                return False
        return True


class QStrictCustomBus(QSparseBus):

    """
    Similar to QSparseBus. The address starts with 1 and addr is always set
    """

    def __init__(self, bus_item, addr_spec, busid, bus_type=None, aobject=None,
                 atype=None, first_port=None):
        super(QStrictCustomBus, self).__init__(bus_item, addr_spec, busid,
                                               bus_type, aobject, atype)
        if first_port:
            self.first_port = first_port

    def _update_device_props(self, device, addr):
        """ in case this is usb-hub update the child port_prefix """
        self._set_device_props(device, addr)


class QUSBBus(QSparseBus):

    """
    USB bus representation including usb-hub handling.
    """

    def __init__(self, length, busid, bus_type, aobject=None,
                 port_prefix=None):
        """
        Bus type have to be generalized and parsed from original bus type:
        (usb-ehci == ehci, ich9-usb-uhci1 == uhci, ...)
        """
        # There are various usb devices for the same bus type, use only portion
        for bus in ('uhci', 'ehci', 'ohci', 'xhci'):
            if bus in bus_type:
                bus_type = bus
                break
        # Usb ports are counted from 1 so the length have to be +1
        super(QUSBBus, self).__init__('bus', [['port'], [length + 1]], busid,
                                      bus_type, aobject)
        self.__port_prefix = port_prefix
        self.__length = length
        self.first_port = [1]

    def _check_bus(self, device):
        """ Check port prefix in order to match addresses in usb-hubs """
        if not super(QUSBBus, self)._check_bus(device):
            return False
        port = device.get_param('port')   # 2.1.6
        if port or port == 0:   # If port is specified
            idx = str(port).rfind('.')
            if idx != -1:   # Strip last number and compare with port_prefix
                return port[:idx] == self.__port_prefix
            # Port is number, match only root usb bus
            elif self.__port_prefix != "":
                return False
        return True

    def _dev2addr(self, device):
        """
        Parse the internal address out of the device
        :param device: qdevices.QBaseDevice device
        :return: internal address  [addr1, addr2, ...]
        """
        value = device.get_param('port')
        if value is None:
            addr = [None]
        else:
            addr = [int(value[len(self.__port_prefix) + 1:])]
        return addr

    def __hook_child_bus(self, device, addr):
        """ If this is usb-hub, add child bus """
        # only usb hub needs customization
        if device.get_param('driver') != 'usb-hub':
            return
        _bus = [_ for _ in device.child_bus if not isinstance(_, QUSBBus)]
        _bus.append(QUSBBus(8, self.busid, self.type, device.get_aid(),
                            str(addr[0])))
        device.child_bus = _bus

    def _set_device_props(self, device, addr):
        """ in case this is usb-hub update the child port_prefix """
        if addr[0] or addr[0] is 0:
            if self.__port_prefix:
                addr = ['%s.%s' % (self.__port_prefix, addr[0])]
        self.__hook_child_bus(device, addr)
        super(QUSBBus, self)._set_device_props(device, addr)

    def _update_device_props(self, device, addr):
        """ in case this is usb-hub update the child port_prefix """
        self._set_device_props(device, addr)


class QDriveBus(QSparseBus):

    """
    QDrive bus representation (single slot, drive=...)
    """

    def __init__(self, busid, aobject=None):
        """
        :param busid: id of the bus (pci.0)
        :param aobject: Related autotest object (image1)
        """
        super(QDriveBus, self).__init__('drive', [[], []], busid, 'QDrive',
                                        aobject)

    def get_free_slot(self, addr_pattern):
        """ Use only drive as slot """
        if 'drive' in self.bus:
            return None
        else:
            return True

    @staticmethod
    def _addr2stor(addr):
        """ address is always drive """
        return 'drive'

    def _update_device_props(self, device, addr):
        """
        Always set -drive property, it's mandatory. Also for hotplug purposes
        store this bus device into hook variable of the device.
        """
        self._set_device_props(device, addr)
        if hasattr(device, 'hook_drive_bus'):
            device.hook_drive_bus = self.get_device()


class QDenseBus(QSparseBus):

    """
    Dense bus representation. The only difference from SparseBus is the output
    string format. DenseBus iterates over all addresses and show free slots
    too. SparseBus on the other hand prints always the device address.
    """

    def _str_devices_long(self):
        """ Show all addresses even when they are unused """
        out = ""
        addr_pattern = [None] * len(self.addr_items)
        addr = self._set_first_addr(addr_pattern)[0]
        while addr:
            dev = self.bus.get(self._addr2stor(addr))
            out += '%s< %4s >%s\n  ' % ('-' * 15, self._addr2stor(addr),
                                        '-' * 15)
            if hasattr(dev, 'str_long'):
                out += dev.str_long().replace('\n', '\n  ')
                out = out[:-3]
            elif isinstance(dev, str):
                out += '"%s"' % dev
            else:
                out += "%s" % dev
            out += '\n'
            addr = self._increment_addr(addr_pattern, addr)
        return out

    def _str_devices(self):
        """ Show all addresses even when they are unused, don't print addr """
        out = '['
        addr_pattern = [None] * len(self.addr_items)
        addr = self._set_first_addr(addr_pattern)[0]
        while addr:
            out += "%s," % self.bus.get(self._addr2stor(addr))
            addr = self._increment_addr(addr_pattern, addr)
        if out[-1] == ',':
            out = out[:-1]
        return out + ']'


class QPCIBus(QSparseBus):

    """
    PCI Bus representation (bus&addr, uses hex digits)
    """

    def __init__(self, busid, bus_type, aobject=None, length=32, first_port=0):
        """ bus&addr, 32 slots """
        super(QPCIBus, self).__init__('bus', [['addr', 'func'], [length, 8]],
                                      busid, bus_type, aobject)
        self.first_port = (first_port, 0)

    @staticmethod
    def _addr2stor(addr):
        """ force all items as hexadecimal values """
        out = ""
        for value in addr:
            if value is None:
                out += '*-'
            else:
                out += '%02x-' % value
        if out:
            return out[:-1]
        else:
            return "*"

    def _dev2addr(self, device):
        """ Read the values in base of 16 (hex) """
        addr = device.get_param('addr')
        if isinstance(addr, int):     # only addr
            return [addr, 0]
        elif not addr:    # not defined
            return [None, 0]
        elif isinstance(addr, str):     # addr or addr.func
            addr = [int(_, 16) for _ in addr.split('.', 1)]
            if len(addr) < 2:   # only addr
                addr.append(0)
        return addr

    def _set_device_props(self, device, addr):
        """ Convert addr to the format used by qtree """
        device.set_param(self.bus_item, self.busid)
        orig_addr = device.get_param('addr')
        if addr[1] or (isinstance(orig_addr, str) and
                       orig_addr.find('.') != -1):
            device.set_param('addr', '%02x.%x' % (addr[0], addr[1]))
        else:
            device.set_param('addr', '%02x' % (addr[0]))

    def _update_device_props(self, device, addr):
        """ Always set properties """
        self._set_device_props(device, addr)

    def _increment_addr(self, addr, last_addr=None):
        """ Don't use multifunction address by default """
        if addr[1] is None:
            addr[1] = 0
        return super(QPCIBus, self)._increment_addr(addr, last_addr=last_addr)


class QPCISwitchBus(QPCIBus):

    """
    PCI Switch bus representation (creates downstream device while inserting
    a device).
    """

    def __init__(self, busid, bus_type, downstream_type, aobject=None):
        super(QPCISwitchBus, self).__init__(busid, bus_type, aobject)
        self.__downstream_ports = {}
        self.__downstream_type = downstream_type

    def add_downstream_port(self, addr):
        """
        Add downstream port of the certain address
        """
        if addr not in self.__downstream_ports:
            bus_id = "%s.%s" % (self.busid, int(addr, 16))
            bus = QPCIBus(bus_id, 'PCIE', bus_id)
            self.__downstream_ports[addr] = bus
            downstream = qdevices.QDevice(self.__downstream_type,
                                          {'id': bus_id,
                                           'bus': self.busid,
                                           'addr': addr},
                                          aobject=self.aobject,
                                          parent_bus={'busid': '_PCI_CHASSIS'},
                                          child_bus=bus)
            return downstream

    def _insert(self, device, addr):
        """
        Instead of the device inserts the downstream port. The device is
        inserted later during _set_device_props into this downstream port.
        """
        _addr = addr.split('-')[0]
        added_devices = []
        downstream = self.add_downstream_port(_addr)
        if downstream is not None:
            added_devices.append(downstream)
            added_devices.extend(super(QPCISwitchBus, self)._insert(downstream,
                                                                    addr))

        bus_id = "%s.%s" % (self.busid, int(_addr, 16))
        device['bus'] = bus_id

        return added_devices

    def _set_device_props(self, device, addr):
        """
        Instead of setting the addr this insert the device into the
        downstream port.
        """
        self.__downstream_ports['%02x' % addr[0]].insert(device)


class QSCSIBus(QSparseBus):

    """
    SCSI bus representation (bus + 2 leves, don't iterate over lun by default)
    """

    def __init__(self, busid, bus_type, addr_spec, aobject=None, atype=None):
        """
        :param busid: id of the bus (mybus.0)
        :param bus_type: type of the bus (virtio-scsi-pci, lsi53c895a, ...)
        :param addr_spec: Ranges of addr_spec [scsiid_range, lun_range]
        :param aobject: Related autotest object (image1)
        :param atype: Autotest bus type
        :type atype: str
        """
        super(QSCSIBus, self).__init__('bus', [['scsi-id', 'lun'], addr_spec],
                                       busid, bus_type, aobject, atype)

    def _increment_addr(self, addr, last_addr=None):
        """
        Qemu doesn't increment lun automatically so don't use it when
        it's not explicitelly specified.
        """
        if addr[1] is None:
            addr[1] = 0
        return super(QSCSIBus, self)._increment_addr(addr, last_addr=last_addr)


class QBusUnitBus(QDenseBus):

    """ Implementation of bus-unit bus (ahci, ide) """

    def __init__(self, busid, bus_type, lengths, aobject=None, atype=None):
        """
        :param busid: id of the bus (mybus.0)
        :type busid: str
        :param bus_type: type of the bus (ahci)
        :type bus_type: str
        :param lenghts: lenghts of [buses, units]
        :type lenghts: list of lists
        :param aobject: Related autotest object (image1)
        :type aobject: str
        :param atype: Autotest bus type
        :type atype: str
        """
        if len(lengths) != 2:
            raise ValueError("len(lenghts) have to be 2 (%s)" % self)
        super(QBusUnitBus, self).__init__('bus', [['bus', 'unit'], lengths],
                                          busid, bus_type, aobject, atype)

    def _update_device_props(self, device, addr):
        """ Always set the properties """
        return self._set_device_props(device, addr)

    def _set_device_props(self, device, addr):
        """This bus is compound of m-buses + n-units, set properties """
        device.set_param('bus', "%s.%s" % (self.busid, addr[0]))
        device.set_param('unit', addr[1])

    def _check_bus(self, device):
        """ This bus is compound of m-buses + n-units, check correct busid """
        bus = device.get_param('bus')
        if isinstance(bus, str):
            bus = bus.rsplit('.', 1)
            if len(bus) == 2 and bus[0] != self.busid:  # aaa.3
                return False
            elif not bus[0].isdigit() and bus[0] != self.busid:     # aaa
                return False
        return True  # None, 5, '3'

    def _dev2addr(self, device):
        """ This bus is compound of m-buses + n-units, parse addr from dev """
        bus = None
        unit = None
        busid = device.get_param('bus')
        if isinstance(busid, str):
            if busid.isdigit():
                bus = int(busid)
            else:
                busid = busid.rsplit('.', 1)
                if len(busid) == 2 and busid[1].isdigit():
                    bus = int(busid[1])
        if isinstance(busid, int):
            bus = busid
        if device.get_param('unit'):
            unit = int(device.get_param('unit'))
        return [bus, unit]


class QAHCIBus(QBusUnitBus):

    """ AHCI bus (ich9-ahci, ahci) """

    def __init__(self, busid, aobject=None):
        """ 6xbus, 2xunit """
        super(QAHCIBus, self).__init__(busid, 'IDE', [6, 1], aobject, 'ahci')


class QIDEBus(QBusUnitBus):

    """ IDE bus (piix3-ide) """

    def __init__(self, busid, aobject=None):
        """ 2xbus, 2xunit """
        super(QIDEBus, self).__init__(busid, 'IDE', [2, 2], aobject, 'ide')


class QFloppyBus(QDenseBus):

    """
    Floppy bus (-global isa-fdc.drive?=$drive)
    """

    def __init__(self, busid, aobject=None):
        """ property <= [driveA, driveB] """
        super(QFloppyBus, self).__init__(None, [['property'], [2]], busid,
                                         'floppy', aobject)

    @staticmethod
    def _addr2stor(addr):
        """ translate as drive$CHAR """
        return "drive%s" % chr(65 + addr[0])  # 'A' + addr

    def _dev2addr(self, device):
        """ Read None, number or drive$CHAR and convert to int() """
        addr = device.get_param('property')
        if isinstance(addr, str):
            if addr.startswith('drive') and len(addr) > 5:
                addr = ord(addr[5])
            elif addr.isdigit():
                addr = int(addr)
        return [addr]

    def _update_device_props(self, device, addr):
        """ Always set props """
        self._set_device_props(device, addr)

    def _set_device_props(self, device, addr):
        """ Change value to drive{A,B,...} """
        device.set_param('property', self._addr2stor(addr))


class QOldFloppyBus(QDenseBus):

    """
    Floppy bus (-drive index=n)
    """

    def __init__(self, busid, aobject=None):
        """ property <= [driveA, driveB] """
        super(QOldFloppyBus, self).__init__(None, [['index'], [2]], busid,
                                            'floppy', aobject)

    def _update_device_props(self, device, addr):
        """ Always set props """
        self._set_device_props(device, addr)

    def _set_device_props(self, device, addr):
        """ Change value to drive{A,B,...} """
        device.set_param('index', self._addr2stor(addr))
