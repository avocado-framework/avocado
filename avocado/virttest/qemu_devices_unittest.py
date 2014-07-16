#!/usr/bin/python
"""
This is a unittest for qemu_devices library.

:author: Lukas Doktor <ldoktor@redhat.com>
:copyright: 2012 Red Hat, Inc.
"""
__author__ = """Lukas Doktor (ldoktor@redhat.com)"""

import re
import unittest
import os

import common
from autotest.client.shared.test_utils import mock
from qemu_devices import qdevices, qbuses, qcontainer
from qemu_devices.utils import DeviceHotplugError, DeviceRemoveError
import data_dir
import qemu_monitor

UNITTEST_DATA_DIR = os.path.join(
    data_dir.get_root_dir(), "virttest", "unittest_data")

# Dummy variables
# qemu-1.5.0 human monitor help output
QEMU_HMP = open(os.path.join(UNITTEST_DATA_DIR, "qemu-1.5.0__hmp_help")).read()
# qemu-1.5.0 QMP monitor commands output
QEMU_QMP = open(os.path.join(UNITTEST_DATA_DIR, "qemu-1.5.0__qmp_help")).read()
# qemu-1.5.0 -help
QEMU_HELP = open(os.path.join(UNITTEST_DATA_DIR, "qemu-1.5.0__help")).read()
# qemu-1.5.0 -devices ?
QEMU_DEVICES = open(
    os.path.join(UNITTEST_DATA_DIR, "qemu-1.5.0__devices_help")).read()
# qemu-1.5.0 -M ?
QEMU_MACHINE = open(
    os.path.join(UNITTEST_DATA_DIR, "qemu-1.5.0__machine_help")).read()


class ParamsDict(dict):

    """ params like dictionary """

    def objects(self, item):
        if self.get(item):
            return self.get(item).split(' ')

    def object_params(self, obj):
        ret = self.copy()
        for (param, value) in self.iteritems():
            if param.endswith('_%s' % obj):
                ret[param[:-len('_%s' % obj)]] = value
        return ret


class MockHMPMonitor(qemu_monitor.HumanMonitor):

    """ Dummy class inherited from qemu_monitor.HumanMonitor """

    def __init__(self):     # pylint: disable=W0231
        self.debug_log = False

    def __del__(self):
        pass


class Devices(unittest.TestCase):

    """ set of qemu devices tests """

    def test_q_base_device(self):
        """ QBaseDevice tests """
        qdevice = qdevices.QBaseDevice('MyType',
                                       {'ParamA': 'ValueA',
                                        'AUTOREMOVE': None},
                                       'Object1',
                                       {'type': 'pci'})
        self.assertEqual(qdevice['ParamA'], 'ValueA', 'Param added during '
                         '__init__ is corrupted %s != %s' % (qdevice['ParamA'],
                                                             'ValueA'))
        qdevice['ParamA'] = 'ValueB'
        qdevice.set_param('BoolTrue', True)
        qdevice.set_param('BoolFalse', 'off', bool)
        qdevice['Empty'] = 'EMPTY_STRING'

        out = """MyType
  aid = None
  aobject = Object1
  parent_bus = {'type': 'pci'}
  child_bus = []
  params:
    ParamA = ValueB
    BoolTrue = on
    BoolFalse = off
    Empty = ""
"""
        self.assertEqual(qdevice.str_long(), out, "Device output doesn't match"
                         "\n%s\n\n%s" % (qdevice.str_long(), out))

    def test_q_string_device(self):
        """ QStringDevice tests """
        qdevice = qdevices.QStringDevice('MyType', {'addr': '0x7'},
                                         cmdline='-qdevice ahci,addr=%(addr)s')
        self.assertEqual(qdevice.cmdline(), '-qdevice ahci,addr=0x7', "Cmdline"
                         " doesn't match expected one:\n%s\n%s"
                         % (qdevice.cmdline(), '-qdevice ahci,addr=0x7'))

    def test_q_device(self):
        """ QDevice tests """
        qdevice = qdevices.QDevice('ahci', {'addr': '0x7'})

        self.assertEqual(str(qdevice), "a'ahci'", "Alternative name error %s "
                         "!= %s" % (str(qdevice), "a'ahci'"))

        qdevice['id'] = 'ahci1'
        self.assertEqual(str(qdevice), "q'ahci1'", "Id name error %s "
                         "!= %s" % (str(qdevice), "q'ahci1'"))

        exp = "device_add ahci,addr=0x7,id=ahci1"
        out = qdevice.hotplug_hmp()
        self.assertEqual(out, exp, "HMP command corrupted:\n%s\n%s"
                         % (out, exp))

        exp = ("('device_add', OrderedDict([('addr', '0x7'), "
               "('driver', 'ahci'), ('id', 'ahci1')]))")
        out = str(qdevice.hotplug_qmp())
        self.assertEqual(out, exp, "QMP command corrupted:\n%s\n%s"
                         % (out, exp))


class Buses(unittest.TestCase):

    """ Set of bus-representation tests """

    def test_q_sparse_bus(self):
        """ Sparse bus tests (general bus testing) """
        bus = qbuses.QSparseBus('bus',
                                (['addr1', 'addr2', 'addr3'], [2, 6, 4]),
                                'my_bus',
                                'bus_type',
                                'autotest_bus')

        qdevice = qdevices.QDevice

        # Correct records
        params = {'addr1': '0', 'addr2': '0', 'addr3': '0', 'bus': 'my_bus'}
        dev = qdevice('dev1', params, parent_bus={'type': 'bus_type'})
        exp = []
        out = bus.insert(dev, False)
        self.assertEqual(out, exp, "Failed to add device; %s != %s\n%s\n\n%s"
                         % (out, exp, dev.str_long(), bus.str_long()))

        params = {'addr1': '1', 'addr2': '0', 'addr3': '0', 'bus': 'my_bus'}
        dev = qdevice('dev2', params, parent_bus={'type': 'bus_type'})
        exp = []
        out = bus.insert(dev, False)
        self.assertEqual(out, exp, "Failed to add device; %s != %s\n%s\n\n%s"
                         % (out, exp, dev.str_long(), bus.str_long()))

        params = {'addr1': '1', 'addr2': '1', 'addr3': '0', 'bus': 'my_bus'}
        dev = qdevice('dev3', params, parent_bus={'type': 'bus_type'})
        exp = []
        out = bus.insert(dev, False)
        self.assertEqual(out, exp, "Failed to add device; %s != %s\n%s\n\n%s"
                         % (out, exp, dev.str_long(), bus.str_long()))

        params = {'addr1': '1', 'addr2': '1', 'addr3': '1', 'bus': 'my_bus'}
        dev = qdevice('dev4', params, parent_bus={'type': 'bus_type'})
        exp = []
        out = bus.insert(dev, False)
        self.assertEqual(out, exp, "Failed to add device; %s != %s\n%s\n\n%s"
                         % (out, exp, dev.str_long(), bus.str_long()))

        params = {'addr1': '1', 'bus': 'my_bus'}
        dev = qdevice('dev5', params, parent_bus={'type': 'bus_type'})
        exp = []
        out = bus.insert(dev, False)
        self.assertEqual(out, exp, "Failed to add device; %s != %s\n%s\n\n%s"
                         % (out, exp, dev.str_long(), bus.str_long()))

        params = {'bus': 'my_bus'}
        dev = qdevice('dev6', params, parent_bus={'type': 'bus_type'})
        exp = []
        out = bus.insert(dev, False)
        self.assertEqual(out, exp, "Failed to add device; %s != %s\n%s\n\n%s"
                         % (out, exp, dev.str_long(), bus.str_long()))

        params = {}
        dev2 = qdevice('dev7', params, parent_bus={'type': 'bus_type'})
        exp = []
        out = bus.insert(dev2, False)
        self.assertEqual(out, exp, "Failed to add device; %s != %s\n%s\n\n%s"
                         % (out, exp, dev2.str_long(), bus.str_long()))

        # Compare short repr
        exp = ("my_bus(bus_type): {0-0-0:a'dev1',0-0-1:a'dev6',0-0-2:a'dev7',"
               "1-0-0:a'dev2',1-0-1:a'dev5',1-1-0:a'dev3',1-1-1:a'dev4'}")
        out = str(bus.str_short())
        self.assertEqual(out, exp, "Short representation corrupted:\n%s\n%s"
                         "\n\n%s" % (out, exp, bus.str_long()))

        # Incorrect records
        # Used address
        params = {'addr1': '0', 'addr2': '0', 'addr3': '0', 'bus': 'my_bus'}
        dev = qdevice('devI1', params, parent_bus={'type': 'bus_type'})
        exp = "UsedSlot"
        out = bus.insert(dev, False)
        self.assertEqual(out, exp, "Added bad device; %s != %s\n%s\n\n%s"
                         % (out, exp, dev.str_long(), bus.str_long()))

        # Out of range address
        params = {'addr1': '0', 'addr2': '6', 'addr3': '0', 'bus': 'my_bus'}
        dev = qdevice('devI2', params, parent_bus={'type': 'bus_type'})
        exp = "BadAddr(False)"
        out = bus.insert(dev, False)
        self.assertEqual(out, exp, "Added bad device; %s != %s\n%s\n\n%s"
                         % (out, exp, dev.str_long(), bus.str_long()))

        # Incorrect bus name
        params = {'bus': 'other_bus'}
        dev = qdevice('devI3', params, parent_bus={'type': 'bus_type'})
        exp = "BusId"
        out = bus.insert(dev, False)
        self.assertEqual(out, exp, "Added bad device; %s != %s\n%s\n\n%s"
                         % (out, exp, dev.str_long(), bus.str_long()))

        # Compare short repr
        exp = ("my_bus(bus_type): {0-0-0:a'dev1',0-0-1:a'dev6',0-0-2:a'dev7',"
               "1-0-0:a'dev2',1-0-1:a'dev5',1-1-0:a'dev3',1-1-1:a'dev4'}")
        out = str(bus.str_short())
        self.assertEqual(out, exp, "Short representation corrupted:\n%s\n%s"
                         "\n\n%s" % (out, exp, bus.str_long()))

        # Compare long repr
        exp = """Bus my_bus, type=bus_type
Slots:
---------------< 1-0-0 >---------------
  device
    aid = None
    aobject = None
    parent_bus = {'type': 'bus_type'}
    child_bus = []
    params:
      bus = my_bus
      addr2 = 0
      addr3 = 0
      addr1 = 1
      driver = dev2
---------------< 1-0-1 >---------------
  device
    aid = None
    aobject = None
    parent_bus = {'type': 'bus_type'}
    child_bus = []
    params:
      bus = my_bus
      addr1 = 1
      driver = dev5
---------------< 1-1-1 >---------------
  device
    aid = None
    aobject = None
    parent_bus = {'type': 'bus_type'}
    child_bus = []
    params:
      bus = my_bus
      addr2 = 1
      addr3 = 1
      addr1 = 1
      driver = dev4
---------------< 1-1-0 >---------------
  device
    aid = None
    aobject = None
    parent_bus = {'type': 'bus_type'}
    child_bus = []
    params:
      bus = my_bus
      addr2 = 1
      addr3 = 0
      addr1 = 1
      driver = dev3
---------------< 0-0-1 >---------------
  device
    aid = None
    aobject = None
    parent_bus = {'type': 'bus_type'}
    child_bus = []
    params:
      bus = my_bus
      driver = dev6
---------------< 0-0-0 >---------------
  device
    aid = None
    aobject = None
    parent_bus = {'type': 'bus_type'}
    child_bus = []
    params:
      bus = my_bus
      addr2 = 0
      addr3 = 0
      addr1 = 0
      driver = dev1
---------------< 0-0-2 >---------------
  device
    aid = None
    aobject = None
    parent_bus = {'type': 'bus_type'}
    child_bus = []
    params:
      driver = dev7
"""
        out = str(bus.str_long())
        self.assertEqual(out, exp, "Long representation corrupted:\n%s\n%s"
                         % (repr(out), exp))

        # Low level functions
        # Get device by object
        exp = dev2
        out = bus.get(dev2)
        self.assertEqual(out, exp, "Failed to get device from bus:\n%s\n%s"
                         "\n\n%s" % (out, exp, bus.str_long()))

        dev2.aid = 'bad_device3'
        exp = dev2
        out = bus.get('bad_device3')
        self.assertEqual(out, exp, "Failed to get device from bus:\n%s\n%s"
                         "\n\n%s" % (out, exp, bus.str_long()))

        exp = None
        out = bus.get('missing_bad_device')
        self.assertEqual(out, exp, "Got device while expecting None:\n%s\n%s"
                         "\n\n%s" % (out, exp, bus.str_long()))

        # Remove all devices
        devs = [dev for dev in bus]
        for dev in devs:
            bus.remove(dev)

        exp = 'Bus my_bus, type=bus_type\nSlots:\n'
        out = str(bus.str_long())
        self.assertEqual(out, exp, "Long representation corrupted:\n%s\n%s"
                         % (out, exp))

    def test_q_pci_bus(self):
        """ PCI bus tests """
        bus = qbuses.QPCIBus('pci.0', 'pci', 'my_pci')
        qdevice = qdevices.QDevice

        # Good devices
        params = {'addr': '0'}
        dev = qdevice('dev1', params, parent_bus={'type': 'pci'})
        exp = []
        out = bus.insert(dev, False)
        self.assertEqual(out, exp, "Failed to add device; %s != %s\n%s\n\n%s"
                         % (out, exp, dev.str_long(), bus.str_long()))

        params = {'addr': 10, 'bus': 'pci.0'}
        dev = qdevice('dev2', params, parent_bus={'type': 'pci'})
        exp = []
        out = bus.insert(dev, False)
        self.assertEqual(out, exp, "Failed to add device; %s != %s\n%s\n\n%s"
                         % (out, exp, dev.str_long(), bus.str_long()))

        params = {'addr': '0x1f'}
        dev = qdevice('dev3', params, parent_bus={'type': 'pci'})
        exp = []
        out = bus.insert(dev, False)
        self.assertEqual(out, exp, "Failed to add device; %s != %s\n%s\n\n%s"
                         % (out, exp, dev.str_long(), bus.str_long()))

        # Compare short repr
        exp = ("pci.0(pci): {00-00:a'dev1',0a-00:a'dev2',1f-00:a'dev3'}")
        out = str(bus.str_short())
        self.assertEqual(out, exp, "Short representation corrupted:\n%s\n%s"
                         "\n\n%s" % (out, exp, bus.str_long()))

        # Incorrect records
        # Used address
        params = {'addr': 0}
        dev = qdevice('devI1', params, parent_bus={'type': 'pci'})
        exp = "UsedSlot"
        out = bus.insert(dev, False)
        self.assertEqual(out, exp, "Added bad device; %s != %s\n%s\n\n%s"
                         % (out, exp, dev.str_long(), bus.str_long()))

        # Out of range address
        params = {'addr': '0xffff'}
        dev = qdevice('devI2', params, parent_bus={'type': 'pci'})
        exp = "BadAddr(False)"
        out = bus.insert(dev, False)
        self.assertEqual(out, exp, "Added bad device; %s != %s\n%s\n\n%s"
                         % (out, exp, dev.str_long(), bus.str_long()))

        # Compare short repr
        exp = ("pci.0(pci): {00-00:a'dev1',0a-00:a'dev2',1f-00:a'dev3'}")
        out = str(bus.str_short())
        self.assertEqual(out, exp, "Short representation corrupted:\n%s\n%s"
                         "\n\n%s" % (out, exp, bus.str_long()))

    def test_q_pci_bus_strict(self):
        """ PCI bus tests in strict_mode (enforce additional options) """
        bus = qbuses.QPCIBus('pci.0', 'pci', 'my_pci')
        qdevice = qdevices.QDevice

        params = {}
        bus.insert(qdevice('dev1', params, parent_bus={'type': 'pci'}), True)
        bus.insert(qdevice('dev2', params, parent_bus={'type': 'pci'}), True)
        bus.insert(qdevice('dev3', params, parent_bus={'type': 'pci'}), True)
        params = {'addr': '0x1f'}
        bus.insert(qdevice('dev1', params, parent_bus={'type': 'pci'}), True)
        params = {'addr': 30}
        bus.insert(qdevice('dev1', params, parent_bus={'type': 'pci'}), True)
        params = {'addr': 12}
        bus.insert(qdevice('dev1', params, parent_bus={'type': 'pci'}), True)

        # All devices will have 'addr' set as we are in the strict mode
        exp = """Bus pci.0, type=pci
Slots:
---------------< 1e-00 >---------------
  device
    aid = None
    aobject = None
    parent_bus = {'type': 'pci'}
    child_bus = []
    params:
      addr = 1e
      driver = dev1
      bus = pci.0
---------------< 02-00 >---------------
  device
    aid = None
    aobject = None
    parent_bus = {'type': 'pci'}
    child_bus = []
    params:
      driver = dev3
      bus = pci.0
      addr = 02
---------------< 1f-00 >---------------
  device
    aid = None
    aobject = None
    parent_bus = {'type': 'pci'}
    child_bus = []
    params:
      addr = 1f
      driver = dev1
      bus = pci.0
---------------< 00-00 >---------------
  device
    aid = None
    aobject = None
    parent_bus = {'type': 'pci'}
    child_bus = []
    params:
      driver = dev1
      bus = pci.0
      addr = 00
---------------< 0c-00 >---------------
  device
    aid = None
    aobject = None
    parent_bus = {'type': 'pci'}
    child_bus = []
    params:
      addr = 0c
      driver = dev1
      bus = pci.0
---------------< 01-00 >---------------
  device
    aid = None
    aobject = None
    parent_bus = {'type': 'pci'}
    child_bus = []
    params:
      driver = dev2
      bus = pci.0
      addr = 01
"""
        out = str(bus.str_long())
        self.assertEqual(out, exp, "Long representation corrupted:\n%s\n%s"
                         % (out, exp))

    def test_usb_bus(self):
        """ Tests the specific handlings of QUSBBus """
        usbc1 = qbuses.QUSBBus(2, 'usb1.0', 'uhci')

        # Insert device into usb controller, default port
        dev = qdevices.QDevice('usb-kbd', parent_bus={'type': 'uhci'})
        assert usbc1.insert(dev) == []

        # Insert usb-hub into usb controller, default port
        dev = qdevices.QDevice('usb-hub', parent_bus={'type': 'uhci'})
        assert usbc1.insert(dev) == []
        hub1 = dev.child_bus[-1]

        # Insert usb-hub into usb-hub, exact port
        dev = qdevices.QDevice('usb-hub', {'port': '2.4'},
                               parent_bus={'type': 'uhci'})
        assert hub1.insert(dev) == []
        hub2 = dev.child_bus[-1]

        # Insert usb-hub into usb-hub in usb-hub, exact port
        dev = qdevices.QDevice('usb-hub', {'port': '2.4.3'},
                               parent_bus={'type': 'uhci'})
        assert hub2.insert(dev) == []
        hub3 = dev.child_bus[-1]
        # verify that port is updated correctly
        self.assertEqual("2.4.3", dev.get_param("port"))

        # Insert usb-device into usb-hub in usb-hub in usb-hub, exact port
        dev = qdevices.QDevice('usb-kbd', {'port': '2.4.3.1'},
                               parent_bus={'type': 'uhci'})
        assert hub3.insert(dev) == []
        # Insert usb-device into usb-hub in usb-hub in usb-hub, default port
        dev = qdevices.QDevice('usb-kbd', parent_bus={'type': 'uhci'})
        assert hub3.insert(dev) == []

        # Try to insert device into specific port which belongs to inferior bus
        out = hub2.insert(qdevices.QDevice('usb-kbd',
                                           {'port': '2.4.3.3'},
                                           parent_bus={'type': 'uhci'}))
        assert out == "BusId"

        # Try to insert device into specific port which belongs to superior bus
        out = hub2.insert(qdevices.QDevice('usb-kbd', {'port': '2.4'},
                                           parent_bus={'type': 'uhci'}))
        assert out == "BusId"

        # Try to insert device into specific port which belongs to same level
        # but different port
        out = hub2.insert(qdevices.QDevice('usb-kbd', {'port': '2.3.4'},
                                           parent_bus={'type': 'uhci'}))
        assert out == "BusId"

        # Force insert device with port which belongs to other hub
        dev = qdevices.QDevice('usb-hub', {'port': '2.4.3.4'},
                               parent_bus={'type': 'uhci'})

        # Check the overall buses correctness
        self.assertEqual("usb1.0(uhci): {1:a'usb-kbd',2:a'usb-hub'}",
                         usbc1.str_short())
        self.assertEqual("usb1.0(uhci): {4:a'usb-hub'}",
                         hub1.str_short())
        self.assertEqual("usb1.0(uhci): {3:a'usb-hub'}",
                         hub2.str_short())
        self.assertEqual("usb1.0(uhci): {1:a'usb-kbd',2:a'usb-kbd'}",
                         hub3.str_short())


class Container(unittest.TestCase):

    """ Tests related to the abstract representation of qemu machine """

    def setUp(self):
        self.god = mock.mock_god(ut=self)
        self.god.stub_function(qcontainer.utils, "system_output")

    def tearDown(self):
        self.god.unstub_all()

    def create_qdev(self, vm_name='vm1', strict_mode="no",
                    allow_hotplugged_vm="yes"):
        """ :return: Initialized qcontainer.DevContainer object """
        qemu_cmd = '/usr/bin/qemu_kvm'
        qcontainer.utils.system_output.expect_call('%s -help' % qemu_cmd,
                                                   timeout=10, ignore_status=True
                                                   ).and_return(QEMU_HELP)
        qcontainer.utils.system_output.expect_call("%s -device ? 2>&1"
                                                   % qemu_cmd, timeout=10,
                                                   ignore_status=True
                                                   ).and_return(QEMU_DEVICES)
        qcontainer.utils.system_output.expect_call("%s -M ?" % qemu_cmd,
                                                   timeout=10, ignore_status=True
                                                   ).and_return(QEMU_MACHINE)
        cmd = "echo -e 'help\nquit' | %s -monitor stdio -vnc none" % qemu_cmd
        qcontainer.utils.system_output.expect_call(cmd, timeout=10,
                                                   ignore_status=True
                                                   ).and_return(QEMU_HMP)
        cmd = ('echo -e \'{ "execute": "qmp_capabilities" }\n'
               '{ "execute": "query-commands", "id": "RAND91" }\n'
               '{ "execute": "quit" }\''
               '| %s -qmp stdio -vnc none | grep return |'
               ' grep RAND91' % qemu_cmd)
        qcontainer.utils.system_output.expect_call(cmd, timeout=10,
                                                   ignore_status=True
                                                   ).and_return('')

        cmd = ('echo -e \'{ "execute": "qmp_capabilities" }\n'
               '{ "execute": "query-commands", "id": "RAND91" }\n'
               '{ "execute": "quit" }\' | (sleep 1; cat )'
               '| %s -qmp stdio -vnc none | grep return |'
               ' grep RAND91' % qemu_cmd)
        qcontainer.utils.system_output.expect_call(cmd, timeout=10,
                                                   ignore_status=True
                                                   ).and_return(QEMU_QMP)

        qdev = qcontainer.DevContainer(qemu_cmd, vm_name, strict_mode, 'no',
                                       allow_hotplugged_vm)

        self.god.check_playback()
        return qdev

    def test_qdev_functional(self):
        """ Test basic qdev workflow """
        qdev = self.create_qdev('vm1')

        # Add basic 'pc' devices
        out = qdev.insert(qdev.machine_by_params(ParamsDict({'machine_type':
                                                             'pc'})))
        assert isinstance(out, list)
        assert len(out) == 6, len(out)

        exp = r"""Devices of vm1:
machine
  aid = __0
  aobject = pci.0
  parent_bus = ()
  child_bus = \[.*QPCIBus.*, .*QStrictCustomBus.*\]
  params:
i440FX
  aid = __1
  aobject = None
  parent_bus = ({'aobject': 'pci.0'},)
  child_bus = \[\]
  params:
    driver = i440FX
    addr = 00
    bus = pci.0
PIIX4_PM
  aid = __2
  aobject = None
  parent_bus = ({'aobject': 'pci.0'},)
  child_bus = \[\]
  params:
    driver = PIIX4_PM
    addr = 01.3
    bus = pci.0
PIIX3
  aid = __3
  aobject = None
  parent_bus = ({'aobject': 'pci.0'},)
  child_bus = \[\]
  params:
    driver = PIIX3
    addr = 01
    bus = pci.0
piix3-ide
  aid = __4
  aobject = None
  parent_bus = ({'aobject': 'pci.0'},)
  child_bus = \[.*QIDEBus.*\]
  params:
    driver = piix3-ide
    addr = 01.1
    bus = pci.0
fdc
  aid = __5
  aobject = None
  parent_bus = \(\)
  child_bus = \[.*QFloppyBus.*\]
  params:"""
        out = qdev.str_long()
        self.assertNotEqual(re.findall(exp, out), None, 'Long representation is'
                            'corrupted:\n%s\n%s' % (out, exp))

        exp = ("Buses of vm1\n"
               "  floppy(floppy): [None,None]\n"
               "  ide(ide): [None,None,None,None]\n"
               "  _PCI_CHASSIS_NR(None): {}\n"
               "  _PCI_CHASSIS(None): {}\n"
               "  pci.0(PCI): {00-00:t'i440FX',01-00:t'PIIX3',"
               "01-01:t'piix3-ide',01-03:t'PIIX4_PM'}")
        out = qdev.str_bus_short()
        assert out == exp, "Bus representation is ocrrupted:\n%s\n%s" % (out,
                                                                         exp)

        # Insert some good devices
        qdevice = qdevices.QDevice

        # Device with child bus
        bus = qbuses.QSparseBus('bus', [['addr'], [6]], 'hba1.0', 'hba',
                                'a_hba')
        dev = qdevice('HBA', {'id': 'hba1', 'addr': 10},
                      parent_bus={'aobject': 'pci.0'}, child_bus=bus)
        out = qdev.insert(dev)
        assert isinstance(out, list), out
        assert len(out) == 1, len(out)

        # Device inside a child bus by type (most common)
        dev = qdevice('dev', {}, parent_bus={'type': 'hba'})
        out = qdev.insert(dev)
        assert isinstance(out, list), out
        assert len(out) == 1, len(out)

        # Device inside a child bus by autotest_id
        dev = qdevice('dev', {}, 'autotest_remove', {'aobject': 'a_hba'})
        out = qdev.insert(dev)
        assert isinstance(out, list), out
        assert len(out) == 1, len(out)

        # Device inside a child bus by busid
        dev = qdevice('dev', {}, 'autoremove', {'busid': 'hba1.0'})
        out = qdev.insert(dev)
        assert isinstance(out, list), out
        assert len(out) == 1, len(out)

        # Check the representation
        exp = ("Devices of vm1: [t'machine',t'i440FX',t'PIIX4_PM',t'PIIX3',"
               "t'piix3-ide',t'fdc',hba1,a'dev',a'dev',a'dev']")
        out = qdev.str_short()
        self.assertEqual(out, exp, "Short representation is corrupted:\n%s\n%s"
                         % (out, exp))
        exp = ("Buses of vm1\n"
               "  hba1.0(hba): {0:a'dev',1:a'dev',2:a'dev'}\n"
               "  floppy(floppy): [None,None]\n"
               "  ide(ide): [None,None,None,None]\n"
               "  _PCI_CHASSIS_NR(None): {}\n"
               "  _PCI_CHASSIS(None): {}\n"
               "  pci.0(PCI): {00-00:t'i440FX',01-00:t'PIIX3',"
               "01-01:t'piix3-ide',01-03:t'PIIX4_PM',0a-00:hba1}")
        out = qdev.str_bus_short()
        assert out == exp, 'Bus representation iscorrupted:\n%s\n%s' % (out,
                                                                        exp)

        # Check the representation
        exp = ("Devices of vm1: [t'machine',t'i440FX',t'PIIX4_PM',t'PIIX3',"
               "t'piix3-ide',t'fdc',hba1,a'dev',a'dev',a'dev']")
        out = qdev.str_short()
        assert out == exp, "Short representation is corrupted:\n%s\n%s" % (out,
                                                                           exp)
        exp = ("Buses of vm1\n"
               "  hba1.0(hba): {0:a'dev',1:a'dev',2:a'dev'}\n"
               "  floppy(floppy): [None,None]\n"
               "  ide(ide): [None,None,None,None]\n"
               "  _PCI_CHASSIS_NR(None): {}\n"
               "  _PCI_CHASSIS(None): {}\n"
               "  pci.0(PCI): {00-00:t'i440FX',01-00:t'PIIX3',"
               "01-01:t'piix3-ide',01-03:t'PIIX4_PM',0a-00:hba1}")
        out = qdev.str_bus_short()
        assert out == exp, 'Bus representation is corrupted:\n%s\n%s' % (out,
                                                                         exp)

        # Now representation contains some devices, play with it a bit
        # length
        out = len(qdev)
        assert out == 10, "Length of qdev is incorrect: %s != %s" % (out, 10)

        # compare
        qdev2 = self.create_qdev('vm1')
        self.assertNotEqual(qdev, qdev2, "This qdev matches empty one:"
                            "\n%s\n%s" % (qdev, qdev2))
        self.assertNotEqual(qdev2, qdev, "Empty qdev matches current one:"
                            "\n%s\n%s" % (qdev, qdev2))
        for _ in xrange(10):
            qdev2.insert(qdevice())
        self.assertNotEqual(qdev, qdev2, "This qdev matches different one:"
                            "\n%s\n%s" % (qdev, qdev2))
        self.assertNotEqual(qdev2, qdev, "Other qdev matches this one:\n%s\n%s"
                            % (qdev, qdev2))
        # cmdline
        exp = ("-M pc -device HBA,id=hba1,addr=0a,bus=pci.0 -device dev "
               "-device dev -device dev")
        out = qdev.cmdline()
        self.assertEqual(out, exp, 'Corrupted qdev.cmdline() output:\n%s\n%s'
                         % (out, exp))

        # get_by_qid (currently we have 2 devices of the same qid)
        out = qdev.get_by_qid('hba1')
        self.assertEqual(len(out), 1, 'Incorrect number of devices by qid '
                         '"hba1": %s != 1\n%s' % (len(out), qdev.str_long()))

        # Remove some devices
        # Remove based on aid
        out = qdev.remove('__6')
        self.assertEqual(out, None, 'Failed to remove device:\n%s\nRepr:\n%s'
                         % ('hba1__0', qdev.str_long()))

        # Remove device which contains other devices (without recursive)
        self.assertRaises(qcontainer.DeviceRemoveError, qdev.remove, 'hba1',
                          False)

        # Remove device which contains other devices (recursive)
        out = qdev.remove('hba1')
        self.assertEqual(out, None, 'Failed to remove device:\n%s\nRepr:\n%s'
                         % ('hba1', qdev.str_long()))

        # Check the representation
        exp = ("Devices of vm1: [t'machine',t'i440FX',t'PIIX4_PM',t'PIIX3',"
               "t'piix3-ide',t'fdc']")
        out = qdev.str_short()
        assert out == exp, "Short representation is corrupted:\n%s\n%s" % (out,
                                                                           exp)
        exp = ("Buses of vm1\n"
               "  floppy(floppy): [None,None]\n"
               "  ide(ide): [None,None,None,None]\n"
               "  _PCI_CHASSIS_NR(None): {}\n"
               "  _PCI_CHASSIS(None): {}\n"
               "  pci.0(PCI): {00-00:t'i440FX',01-00:t'PIIX3',"
               "01-01:t'piix3-ide',01-03:t'PIIX4_PM'}")
        out = qdev.str_bus_short()
        assert out == exp, 'Bus representation is corrupted:\n%s\n%s' % (out,
                                                                         exp)

    def test_qdev_hotplug(self):
        """ Test the hotplug/unplug functionality """
        qdev = self.create_qdev('vm1', False, True)
        devs = qdev.machine_by_params(ParamsDict({'machine_type': 'pc'}))
        for dev in devs:
            qdev.insert(dev)
        monitor = MockHMPMonitor()

        out = qdev.get_state()
        assert out == -1, ("Status after init is not -1"
                           " (%s)" % out)
        out = len(qdev)
        assert out == 6, "Number of devices of this VM is not 5 (%s)" % out

        dev1, dev2 = qdev.images_define_by_variables('disk', '/tmp/a',
                                                     fmt="virtio")

        out = dev1.hotplug_hmp()
        exp = "drive_add auto id=drive_disk,if=none,file=/tmp/a"
        assert out == exp, ("Hotplug command of drive is incorrect:\n%s\n%s"
                            % (exp, out))

        # hotplug of drive will return "  OK" (pass)
        dev1.hotplug = lambda _monitor: "OK"
        dev1.verify_hotplug = lambda _out, _monitor: True
        out, ver_out = qdev.simple_hotplug(dev1, monitor)
        assert out == "OK", "Return value of hotplug is not OK (%s)" % out
        assert ver_out is True, ("Return value of hotplug"
                                 " is not True (%s)" % ver_out)
        out = qdev.get_state()
        assert out == 0, ("Status after verified hotplug is not 0 (%s)" % out)

        # hotplug of virtio-blk-pci will return ""
        out = dev2.hotplug_hmp()
        exp = "device_add virtio-blk-pci,id=disk,drive=drive_disk"
        assert out == exp, ("Hotplug command of device is incorrect:\n%s\n%s"
                            % (exp, out))
        dev2.hotplug = lambda _monitor: ""
        dev2.verify_hotplug = lambda _out, _monitor: ""
        out, ver_out = qdev.simple_hotplug(dev2, monitor)
        # automatic verification is not supported, hotplug returns the original
        # monitor message ("")
        assert ver_out == "", ("Return value of hotplug is"
                               " not "" (%s)" % ver_out)
        assert out == "", 'Return value of hotplug is not "" (%s)' % out
        out = qdev.get_state()
        assert out == 1, ("Status after verified hotplug is not 1 (%s)" % out)
        qdev.hotplug_verified()
        out = qdev.get_state()
        assert out == 0, ("Status after verified hotplug is not 0 (%s)" % out)

        out = len(qdev)
        assert out == 8, "Number of devices of this VM is not 8 (%s)" % out

        # Hotplug is expected to pass but monitor reports failure
        dev3 = qdevices.QDrive('a_dev1')
        dev3.hotplug = lambda _monitor: ("could not open disk image /tmp/qqq: "
                                         "No such file or directory")

        out, ver_out = qdev.simple_hotplug(dev3, monitor)
        exp = "could not open disk image /tmp/qqq: No such file or directory"
        assert out, "Return value of hotplug is incorrect:\n%s\n%s" % (out,
                                                                       exp)
        out = qdev.get_state()
        assert out == 1, ("Status after failed hotplug is not 1 (%s)" % out)
        # device is still in qdev, but is not in qemu, we should remove it
        qdev.remove(dev3, recursive=False)
        out = qdev.get_state()
        assert out == 1, ("Status after verified hotplug is not 1 (%s)" % out)
        qdev.hotplug_verified()
        out = qdev.get_state()
        assert out == 0, ("Status after verified hotplug is not 0 (%s)" % out)

        # Hotplug is expected to fail, qdev should stay unaffected
        dev4 = qdevices.QBaseDevice("bad_dev", parent_bus={'type': "XXX"})
        dev4.hotplug = lambda _monitor: ("")
        self.assertRaises(qcontainer.DeviceHotplugError, qdev.simple_hotplug,
                          dev4, True)
        out = qdev.get_state()
        assert out == 0, "Status after impossible hotplug is not 0 (%s)" % out

        # Unplug
        # Unplug used drive (automatic verification not supported)
        out = dev1.unplug_hmp()
        exp = "drive_del drive_disk"
        assert out == exp, ("Hotplug command of device is incorrect:\n%s\n%s"
                            % (exp, out))
        dev1.unplug = lambda _monitor: ""
        dev1.verify_unplug = lambda _monitor, _out: ""
        out, ver_out = qdev.simple_unplug(dev1, monitor)
        # I verified, that device was unplugged successfully
        qdev.hotplug_verified()
        out = qdev.get_state()
        assert out == 0, ("Status after verified hotplug is not 0 (%s)" % out)
        out = len(qdev)
        assert out == 7, "Number of devices of this VM is not 7 (%s)" % out
        # Removal of drive should also set drive of the disk device to None
        out = dev2.get_param('drive')
        assert out is None, "Drive was not removed from disk device"

    # pylint: disable=W0212
    def test_qdev_low_level(self):
        """ Test low level functions """
        qdev = self.create_qdev('vm1')

        # Representation state (used for hotplug or other nasty things)
        out = qdev.get_state()
        assert out == -1, "qdev state is incorrect %s != %s" % (out, 1)

        qdev.set_dirty()
        out = qdev.get_state()
        self.assertEqual(out, 1, "qdev state is incorrect %s != %s" % (out, 1))

        qdev.set_dirty()
        out = qdev.get_state()
        self.assertEqual(out, 2, "qdev state is incorrect %s != %s" % (out, 1))

        qdev.set_clean()
        out = qdev.get_state()
        self.assertEqual(out, 1, "qdev state is incorrect %s != %s" % (out, 1))

        qdev.set_clean()
        out = qdev.get_state()
        self.assertEqual(out, 0, "qdev state is incorrect %s != %s" % (out, 1))

        qdev.reset_state()
        out = qdev.get_state()
        assert out == -1, "qdev state is incorrect %s != %s" % (out, 1)

        # __create_unique_aid
        dev = qdevices.QDevice()
        qdev.insert(dev)
        out = dev.get_aid()
        self.assertEqual(out, '__0', "incorrect aid %s != %s" % (out, '__0'))

        dev = qdevices.QDevice(None, {'id': 'qid'})
        qdev.insert(dev)
        out = dev.get_aid()
        self.assertEqual(out, 'qid', "incorrect aid %s != %s" % (out, 'qid'))

        # has_option
        out = qdev.has_option('device')
        self.assertEqual(out, True)

        out = qdev.has_option('missing_option')
        self.assertEqual(out, False)

        # has_device
        out = qdev.has_device('ide-drive')
        self.assertEqual(out, True)

        out = qdev.has_device('missing_device')
        self.assertEqual(out, False)

        # get_help_text
        out = qdev.get_help_text()
        self.assertEqual(out, QEMU_HELP)

        # has_hmp_cmd
        self.assertTrue(qdev.has_hmp_cmd('pcie_aer_inject_error'))
        self.assertTrue(qdev.has_hmp_cmd('c'))
        self.assertTrue(qdev.has_hmp_cmd('cont'))
        self.assertFalse(qdev.has_hmp_cmd('off'))
        self.assertFalse(qdev.has_hmp_cmd('\ndump-guest-memory'))
        self.assertFalse(qdev.has_hmp_cmd('The'))

        # has_qmp_cmd
        self.assertTrue(qdev.has_qmp_cmd('device_add'))
        self.assertFalse(qdev.has_qmp_cmd('RAND91'))

        # Add some buses
        bus1 = qbuses.QPCIBus('pci.0', 'pci', 'a_pci0')
        qdev.insert(qdevices.QDevice(params={'id': 'pci0'},
                                     child_bus=bus1))
        bus2 = qbuses.QPCIBus('pci.1', 'pci', 'a_pci1')
        qdev.insert(qdevices.QDevice(child_bus=bus2))
        bus3 = qbuses.QPCIBus('pci.2', 'pci', 'a_pci2')
        qdev.insert(qdevices.QDevice(child_bus=bus3))
        bus4 = qbuses.QPCIBus('pcie.0', 'pcie', 'a_pcie0')
        qdev.insert(qdevices.QDevice(child_bus=bus4))

        # get_buses (all buses of this type)
        out = qdev.get_buses({'type': 'pci'})
        self.assertEqual(len(out), 3, 'get_buses should return 3 buses but '
                         'returned %s instead:\n%s' % (len(out), out))

        # get_first_free_bus (last added bus of this type)
        out = qdev.get_first_free_bus({'type': 'pci'}, [None, None])
        self.assertEqual(bus3, out)

        # fill the first pci bus
        for _ in xrange(32):
            qdev.insert(qdevices.QDevice(parent_bus={'type': 'pci'}))

        # get_first_free_bus (last one is full, return the previous one)
        out = qdev.get_first_free_bus({'type': 'pci'}, [None, None])
        self.assertEqual(bus2, out)

        # list_named_buses
        out = qdev.list_missing_named_buses('pci.', 'pci', 5)
        self.assertEqual(len(out), 2, 'Number of missing named buses is '
                         'incorrect: %s != %s\n%s' % (len(out), 2, out))
        out = qdev.list_missing_named_buses('pci.', 'abc', 5)
        self.assertEqual(len(out), 5, 'Number of missing named buses is '
                         'incorrect: %s != %s\n%s' % (len(out), 2, out))

        # idx_of_next_named_bus
        out = qdev.idx_of_next_named_bus('pci.')
        self.assertEqual(out, 3, 'Incorrect idx of next named bus: %s !='
                         ' %s' % (out, 3))

        # get_children
        dev = qdevices.QDevice(parent_bus={'aobject': 'a_pci0'})
        bus = qbuses.QPCIBus('test1', 'test', 'a_test1')
        dev.add_child_bus(bus)
        bus = qbuses.QPCIBus('test2', 'test', 'a_test2')
        dev.add_child_bus(bus)
        qdev.insert(dev)
        qdev.insert(qdevices.QDevice(parent_bus={'aobject': 'a_test1'}))
        qdev.insert(qdevices.QDevice(parent_bus={'aobject': 'a_test2'}))
        out = dev.get_children()
        assert len(out) == 2, ("Not all children were listed %d != 2:\n%s"
                               % (len(out), out))

        out = bus.get_device()
        assert out == dev, ("bus.get_device() returned different device "
                            "than the one in which it was plugged:\n"
                            "%s\n%s\n%s" % (out.str_long(), dev.str_long(),
                                            qdev.str_long()))
    # pylint: enable=W0212

    def test_qdev_equal(self):
        qdev1 = self.create_qdev('vm1', allow_hotplugged_vm='no')
        qdev2 = self.create_qdev('vm1', allow_hotplugged_vm='no')
        qdev3 = self.create_qdev('vm1', allow_hotplugged_vm='yes')
        monitor = MockHMPMonitor()

        assert qdev1 == qdev2, ("Init qdevs are not alike\n%s\n%s"
                                % (qdev1.str_long(), qdev2.str_long()))

        # Insert a device to qdev1
        dev = qdevices.QDevice('dev1', {'id': 'dev1'})
        qdev1.insert(dev)

        assert qdev1 != qdev2, ("Different qdevs match:\n%s\n%s"
                                % (qdev1.str_long(), qdev2.str_long()))

        # Insert similar device to qdev2
        dev = qdevices.QDevice('dev1', {'id': 'dev1'})
        qdev2.insert(dev)

        assert qdev1 == qdev2, ("Similar qdevs are not alike\n%s\n%s"
                                % (qdev1.str_long(), qdev2.str_long()))

        # Hotplug similar device to qdev3
        dev = qdevices.QDevice('dev1', {'id': 'dev1'})
        dev.hotplug = lambda _monitor: ""   # override the hotplug method
        dev.verify_hotplug = lambda _out, _monitor: True
        qdev3.simple_hotplug(dev, monitor)
        assert qdev1 == qdev3, ("Similar hotplugged qdevs are not alike\n%s\n"
                                "%s" % (qdev1.str_long(), qdev2.str_long()))

        # Eq. is not symmetrical, qdev1 doesn't allow hotplugged VMs.
        assert qdev3 != qdev1, ("Similar hotplugged qdevs match even thought "
                                "qdev1 doesn't allow hotplugged VM\n%s\n%s"
                                % (qdev1.str_long(), qdev2.str_long()))

        qdev2.__qemu_help = "I support only this :-)"  # pylint: disable=W0212
        assert qdev1 == qdev2, ("qdevs of different qemu versions match:\n%s\n"
                                "%s" % (qdev1.str_long(), qdev2.str_long()))

    def test_pci(self):
        qdev = self.create_qdev('vm1')
        devs = qdev.machine_by_params(ParamsDict({'machine_type': 'pc'}))
        for dev in devs:
            qdev.insert(dev)
        # machine creates main pci (pci.0)
        # buses root.1 pci_switch pci_bridge
        # root.1: ioh3420(pci.0)
        # pci_switch: x3130(root.1)
        # pci_bridge: pci-bridge(root.1)
        devs = qdev.pcic_by_params('root.1', {'pci_bus': 'pci.0',
                                              'type': 'ioh3420'})
        qdev.insert(devs)
        devs = qdev.pcic_by_params('pci_switch', {'pci_bus': 'root.1',
                                                  'type': 'x3130'})

        qdev.insert(devs)
        devs = qdev.pcic_by_params('pci_bridge', {'pci_bus': 'root.1',
                                                  'type': 'pci-bridge'})
        qdev.insert(devs)

        qdev.insert(qdevices.QDevice("ahci", {'id': 'in_bridge'},
                                     parent_bus={'type': ('PCI', 'PCIE'),
                                                 'aobject': 'pci_bridge'}))

        qdev.insert(qdevices.QDevice("ahci", {'id': 'in_switch1'},
                                     parent_bus={'type': ('PCI', 'PCIE'),
                                                 'aobject': 'pci_switch'}))
        qdev.insert(qdevices.QDevice("ahci", {'id': 'in_switch2'},
                                     parent_bus={'type': ('PCI', 'PCIE'),
                                                 'aobject': 'pci_switch'}))
        qdev.insert(qdevices.QDevice("ahci", {'id': 'in_switch3'},
                                     parent_bus={'type': ('PCI', 'PCIE'),
                                                 'aobject': 'pci_switch'}))

        qdev.insert(qdevices.QDevice("ahci", {'id': 'in_root1'},
                                     parent_bus={'type': ('PCI', 'PCIE'),
                                                 'aobject': 'root.1'}))

        qdev.insert(qdevices.QDevice("ahci", {'id': 'in_pci.0'},
                                     parent_bus={'type': ('PCI', 'PCIE'),
                                                 'aobject': 'pci.0'}))

        exp = ("-M pc -device ioh3420,id=root.1,bus=pci.0,addr=02 "
               "-device x3130-upstream,id=pci_switch,bus=root.1,addr=00 "
               "-device pci-bridge,id=pci_bridge,bus=root.1,addr=01,"
               "chassis_nr=1 -device ahci,id=in_bridge,bus=pci_bridge,addr=01"
               " -device xio3130-downstream,bus=pci_switch,id=pci_switch.0,"
               "addr=00,chassis=1 -device ahci,id=in_switch1,bus=pci_switch.0"
               ",addr=00 "
               "-device xio3130-downstream,bus=pci_switch,id=pci_switch.1,"
               "addr=01,chassis=2 -device ahci,id=in_switch2,bus=pci_switch.1"
               ",addr=00 "
               "-device xio3130-downstream,bus=pci_switch,id=pci_switch.2,"
               "addr=02,chassis=3 -device ahci,id=in_switch3,bus=pci_switch.2"
               ",addr=00 "
               "-device ahci,id=in_root1,bus=root.1,addr=02 "
               "-device ahci,id=in_pci.0,bus=pci.0,addr=03")
        out = qdev.cmdline()
        assert out == exp, (out, exp)

if __name__ == "__main__":
    unittest.main()
