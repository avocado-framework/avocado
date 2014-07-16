#!/usr/bin/python

import unittest
import time
import logging
import sys
import random
import os
import shelve

import common
from autotest.client import utils
from autotest.client.shared.test_utils import mock
import utils_net
import utils_misc
import cartesian_config
import utils_params
import propcan


class FakeVm(object):

    def __init__(self, vm_name, params):
        self.name = vm_name
        self.params = params
        self.vm_type = self.params.get('vm_type')
        self.driver_type = self.params.get('driver_type')
        self.instance = ("%s-%s" % (
            time.strftime("%Y%m%d-%H%M%S"),
            utils_misc.generate_random_string(16)))

    def get_params(self):
        return self.params

    def is_alive(self):
        logging.info("Fake VM %s (instance %s)", self.name, self.instance)


class TestBridge(unittest.TestCase):

    class FakeCmd(object):
        iter = 0

        def __init__(self, *args, **kargs):
            self.fake_cmds = [
                """bridge name    bridge id        STP enabled    interfaces
virbr0        8000.52540018638c    yes        virbr0-nic
virbr1        8000.525400c0b080    yes        em1
                                              virbr1-nic
""",
                """bridge name    bridge id        STP enabled    interfaces
virbr0        8000.52540018638c    yes
""",
                """bridge name    bridge id        STP enabled    interfaces
""",
                """bridge name    bridge id        STP enabled    interfaces
virbr0        8000.52540018638c    yes        virbr0-nic
                                              virbr2-nic
                                              virbr3-nic
virbr1        8000.525400c0b080    yes        em1
                                              virbr1-nic
                                              virbr4-nic
                                              virbr5-nic
virbr2        8000.525400c0b080    yes        em1
                                              virbr10-nic
                                              virbr40-nic
                                              virbr50-nic
"""]

            self.stdout = self.get_stdout()
            self.__class__.iter += 1

        def get_stdout(self):
            return self.fake_cmds[self.__class__.iter]

    def setUp(self):
        self.god = mock.mock_god(ut=self)

        def utils_run(*args, **kargs):
            return TestBridge.FakeCmd(*args, **kargs)

        self.god.stub_with(utils, 'run', utils_run)

    def test_getstructure(self):

        br = utils_net.Bridge().get_structure()
        self.assertEqual(br, {'virbr1': ['em1', 'virbr1-nic'],
                              'virbr0': ['virbr0-nic']})

        br = utils_net.Bridge().get_structure()
        self.assertEqual(br, {'virbr0': []})

        br = utils_net.Bridge().get_structure()
        self.assertEqual(br, {})

        br = utils_net.Bridge().get_structure()
        self.assertEqual(br, {'virbr2': ['em1', 'virbr10-nic',
                                         'virbr40-nic', 'virbr50-nic'],
                              'virbr1': ['em1', 'virbr1-nic', 'virbr4-nic',
                                         'virbr5-nic'],
                              'virbr0': ['virbr0-nic', 'virbr2-nic',
                                         'virbr3-nic']})

    def tearDown(self):
        self.god.unstub_all()


class TestVirtIface(unittest.TestCase):

    VirtIface = utils_net.VirtIface

    def setUp(self):
        logging.disable(logging.INFO)
        logging.disable(logging.WARNING)
        utils_net.VirtIface.LASTBYTE = -1  # Restart count at zero
        # These warnings are annoying during testing
        utils_net.VMNet.DISCARD_WARNINGS - 1

    def loop_assert(self, virtiface, test_keys, what_func):
        for propertea in test_keys:
            attr_access_value = getattr(virtiface, propertea)
            can_access_value = virtiface[propertea]
            get_access_value = virtiface.get(propertea, None)
            expected_value = what_func(propertea)
            self.assertEqual(attr_access_value, can_access_value)
            self.assertEqual(can_access_value, expected_value)
            self.assertEqual(get_access_value, expected_value)

    def test_half_set(self):
        half_prop_end = (len(self.VirtIface.__all_slots__) / 2) + 1
        props = {}
        for propertea in self.VirtIface.__all_slots__[0:half_prop_end]:
            props[propertea] = utils_misc.generate_random_string(16)
        virtiface = self.VirtIface(props)
        what_func = lambda propertea: props[propertea]
        self.loop_assert(virtiface, props.keys(), what_func)

    def test_full_set(self):
        props = {}
        for propertea in self.VirtIface.__all_slots__:
            props[propertea] = utils_misc.generate_random_string(16)
        virtiface = self.VirtIface(props)
        what_func = lambda propertea: props[propertea]
        self.loop_assert(virtiface, props.keys(), what_func)

    def test_apendex_set(self):
        """
        Verify container ignores unknown key names
        """
        props = {}
        for propertea in self.VirtIface.__all_slots__:
            props[propertea] = utils_misc.generate_random_string(16)
        more_props = {}
        for _ in xrange(0, 16):
            key = utils_misc.generate_random_string(16)
            value = utils_misc.generate_random_string(16)
            more_props[key] = value
        # Keep separated for testing
        apendex_set = {}
        apendex_set.update(props)
        apendex_set.update(more_props)
        virtiface = self.VirtIface(apendex_set)
        what_func = lambda propertea: props[propertea]
        # str(props) guarantees apendex set wasn't incorporated
        self.loop_assert(virtiface, props.keys(), what_func)

    def test_mac_completer(self):
        for test_mac in ['9a', '01:02:03:04:05:06', '00', '1:2:3:4:5:6',
                         '0a:0b:0c:0d:0e:0f', 'A0:B0:C0:D0:E0:F0',
                         "01:02:03:04:05:", "01:02:03:04::", "01:02::::",
                         "00:::::::::::::::::::", ":::::::::::::::::::",
                         ":"]:
            # Tosses an exception if test_mac can't be completed
            self.VirtIface.complete_mac_address(test_mac)
        self.assertRaises(TypeError, self.VirtIface.complete_mac_address,
                          '01:f0:0:ba:r!:00')
        self.assertRaises(TypeError, self.VirtIface.complete_mac_address,
                          "01:02:03::05:06")


class TestQemuIface(TestVirtIface):

    def setUp(self):
        super(TestQemuIface, self).setUp()
        self.VirtIface = utils_net.QemuIface


class TestLibvirtIface(TestVirtIface):

    def setUp(self):
        super(TestLibvirtIface, self).setUp()
        self.VirtIface = utils_net.LibvirtIface


class TestVmNetStyle(unittest.TestCase):

    def setUp(self):
        logging.disable(logging.INFO)
        logging.disable(logging.WARNING)

    def get_style(self, vm_type, driver_type):
        return utils_net.VMNetStyle.get_style(vm_type, driver_type)

    def test_default_default(self):
        style = self.get_style(utils_misc.generate_random_string(16),
                               utils_misc.generate_random_string(16))
        self.assertEqual(style['mac_prefix'], '9a')
        self.assertEqual(style['container_class'], utils_net.QemuIface)
        self.assert_(issubclass(style['container_class'], utils_net.VirtIface))

    def test_libvirt(self):
        style = self.get_style('libvirt',
                               utils_misc.generate_random_string(16))
        self.assertEqual(style['container_class'], utils_net.LibvirtIface)
        self.assert_(issubclass(style['container_class'], utils_net.VirtIface))


class TestVmNet(unittest.TestCase):

    def setUp(self):
        logging.disable(logging.INFO)
        logging.disable(logging.WARNING)
        utils_net.VirtIface.LASTBYTE = -1  # Restart count at zero
        # These warnings are annoying during testing
        utils_net.VMNet.DISCARD_WARNINGS - 1

    def test_string_container(self):
        self.assertRaises(TypeError, utils_net.VMNet, str, ["Foo"])

    def test_VirtIface_container(self):
        test_data = [
            {'nic_name': 'nic1',
             'mac': '0a'},
            {'nic_name': ''},  # test data index 1
            {'foo': 'bar',
             'nic_name': 'nic2'},
            {'nic_name': 'nic3',
             'mac': '01:02:03:04:05:06'}
        ]
        self.assertRaises(utils_net.VMNetError,
                          utils_net.VMNet,
                          utils_net.VirtIface, test_data)
        del test_data[1]
        vmnet = utils_net.VMNet(utils_net.VirtIface, test_data)
        self.assertEqual(vmnet[0].nic_name, test_data[0]['nic_name'])
        self.assertEqual(vmnet['nic1'].__class__, utils_net.VirtIface)
        self.assertEqual(False, hasattr(vmnet['nic1'], 'mac'))
        self.assertEqual(False, 'mac' in vmnet['nic1'].keys())
        self.assertEqual(vmnet.nic_name_list(), ['nic1', 'nic2', 'nic3'])
        self.assertEqual(vmnet.nic_name_index('nic2'), 1)
        self.assertRaises(TypeError, vmnet.nic_name_index, 0)
        self.assertEqual(True, hasattr(vmnet[2], 'mac'))
        self.assertEqual(test_data[2]['mac'], vmnet[2]['mac'])


class TestVmNetSubclasses(unittest.TestCase):

    nettests_cartesian = ("""
    variants:
        - onevm:
            vms=vm1
        - twovms:
            vms=vm1 vm2
        - threevms:
            vms=vm1 vm2 vm3

    variants:
        - typeundefined:
        - libvirt:
            vm_type = libvirt
            variants:
                - unsetdrivertype:
                - xen:
                    driver_type = xen
                    nics=nic1
                - qemu:
                    driver_type = qemu
                    nics=nic1 nic2
                - kvm:
                    driver_type = kvm
                    nics=nic1 nic2 nic3
                - lxc:
                    driver_type = lxc
                    nics=nic1 nic2 nic3 nic4
        - qemu:
            vm_type = qemu
            variants:
                - unsetdrivertype:
                - kvm:
                    driver_type = kvm
                - qemu:
                    driver_type = qemu

    variants:
        -propsundefined:
        -defaultprops:
            mac = 9a
            nic_model = virtio
            nettype = bridge
            netdst = virbr0
            vlan = 0
        -mixedpropsone:
            mac_nic1 = 9a:01
            nic_model_nic1 = rtl8139
            nettype_nic1 = bridge
            netdst_nic1 = virbr1
            vlan_nic1 = 1
            ip_nic1 = 192.168.122.101
            netdev_nic1 = foobar
        -mixedpropstwo:
            mac_nic2 = 9a:02
            nic_model_nic2 = e1000
            nettype_nic2 = network
            netdst_nic2 = eth2
            vlan_nic2 = 2
            ip_nic2 = 192.168.122.102
            netdev_nic2 = barfoo
        -mixedpropsthree:
            mac_nic1 = 01:02:03:04:05:06
            mac_nic2 = 07:08:09:0a:0b:0c
            mac_nic4 = 0d:0e:0f:10:11:12
        -mixedpropsthree:
            nettype_nic3 = bridge
            netdst_nic3 = virbr3
            netdev_nic3 = qwerty
    """)

    mac_prefix = "01:02:03:04:05:"
    db_filename = '/dev/shm/UnitTest_AddressPool'
    db_item_count = 0
    counter = 0  # for printing dots

    def setUp(self):
        """
        Runs before every test
        """
        logging.disable(logging.INFO)
        logging.disable(logging.WARNING)
        # MAC generator produces from incrementing byte list
        # at random starting point (class property).
        # make sure it starts counting at zero before every test
        utils_net.VirtIface.LASTBYTE = -1
        # These warnings are annoying during testing
        utils_net.VMNet.DISCARD_WARNINGS - 1
        parser = cartesian_config.Parser()
        parser.parse_string(self.nettests_cartesian)
        self.CartesianResult = []
        for d in parser.get_dicts():
            params = utils_params.Params(d)
            self.CartesianResult.append(params)
            for vm_name in params.objects('vms'):
                vm = params.object_params(vm_name)
                nics = vm.get('nics')
                if nics and len(nics.split()) > 0:
                    self.db_item_count += 1

    def fakevm_generator(self):
        for params in self.CartesianResult:
            for vm_name in params.get('vms').split():
                # Return iterator covering all types of vms
                # in exactly the same order each time. For more info, see:
                # http://docs.python.org/reference/simple_stmts.html#yield
                yield FakeVm(vm_name, params)

    def zero_counter(self, increment=100):
        # rough total, doesn't include the number of vms
        self.increment = increment
        self.counter = 0
        sys.stdout.write(".")
        sys.stdout.flush()

    def print_and_inc(self):
        self.counter += 1
        if self.counter >= self.increment:
            self.counter = 0
            sys.stdout.write(".")
            sys.stdout.flush()

    def test_cmp_Virtnet(self):
        self.zero_counter()
        to_test = 600  # Random generator slows this test way down
        for fakevm1 in self.fakevm_generator():
            to_test -= 1
            if to_test < 1:
                break
            fvm1p = fakevm1.get_params()
            fakevm1.virtnet = utils_net.VirtNet(fvm1p, fakevm1.name,
                                                fakevm1.instance,
                                                self.db_filename)
            if len(fakevm1.virtnet) < 2:
                continue
            fakevm2 = FakeVm(fakevm1.name + "_2", fvm1p)
            fakevm2.virtnet = utils_net.VirtNet(fvm1p, fakevm2.name,
                                                fakevm2.instance,
                                                self.db_filename)
            # Verify nic order doesn't matter
            fvm3p = utils_params.Params(fvm1p.items())  # work on copy
            nic_list = fvm1p.object_params(fakevm1.name).get(
                "nics", fvm1p.get('nics', "")).split()
            random.shuffle(nic_list)
            fvm3p['nics'] = " ".join(nic_list)
            fakevm3 = FakeVm(fakevm1.name + "_3", fvm3p)
            fakevm3.virtnet = utils_net.VirtNet(fvm3p, fakevm3.name,
                                                fakevm3.instance,
                                                self.db_filename)
            self.assertTrue(fakevm1.virtnet == fakevm1.virtnet)
            self.assertTrue(fakevm1.virtnet == fakevm2.virtnet)
            self.assertTrue(fakevm1.virtnet == fakevm3.virtnet)
            self.assertTrue(fakevm2.virtnet == fakevm3.virtnet)
            if len(fakevm1.virtnet) > 1:
                del fakevm1.virtnet[0]
                self.assertFalse(fakevm1.virtnet == fakevm2.virtnet)
                self.assertFalse(fakevm1.virtnet == fakevm3.virtnet)
                self.assertTrue(fakevm1.virtnet != fakevm2.virtnet)
                self.assertTrue(fakevm1.virtnet != fakevm3.virtnet)
            self.print_and_inc()

    def test_01_Params(self):
        """
        Load Cartesian combinatorial result verifies against all styles of VM.

        Note: There are some cases where the key should NOT be set, in this
              case an exception is caught prior to verifying
        """
        self.zero_counter()
        for fakevm in self.fakevm_generator():
            test_params = fakevm.get_params()
            virtnet = utils_net.ParamsNet(test_params,
                                          fakevm.name)
            self.assert_(virtnet.container_class)
            self.assert_(virtnet.mac_prefix)
            self.assert_(issubclass(virtnet.__class__, list))
            # Assume params actually came from CartesianResult because
            # Checking this takes a very long time across all combinations
            param_nics = test_params.object_params(fakevm.name).get(
                "nics", test_params.get('nics', "")).split()
            # Size of list should match number of nics configured
            self.assertEqual(len(param_nics), len(virtnet))
            # Test each interface data
            for virtnet_index in xrange(0, len(virtnet)):
                # index correspondence already established/asserted
                virtnet_nic = virtnet[virtnet_index]
                params_nic = param_nics[virtnet_index]
                self.assert_(issubclass(virtnet_nic.__class__,
                                        propcan.PropCan))
                self.assertEqual(virtnet_nic.nic_name, params_nic,
                                 "%s != %s" % (virtnet_nic.nic_name,
                                               params_nic))
                # __slots__ functionality established/asserted elsewhere
                props_to_check = list(utils_net.VirtIface.__all_slots__)
                # other tests check mac address handling
                del props_to_check[props_to_check.index('mac')]
                for propertea in props_to_check:
                    params_propertea = test_params.object_params(params_nic
                                                                 ).get(propertea)
                    # Double-verify dual-mode access works
                    try:
                        virtnet_propertea1 = getattr(virtnet_nic, propertea)
                        virtnet_propertea2 = virtnet_nic[propertea]
                    except (KeyError, AttributeError):
                        # This style may not support all properties, skip
                        continue
                    # Only check stuff cartesian config actually set
                    if params_propertea:
                        self.assertEqual(params_propertea, virtnet_propertea1)
                        self.assertEqual(
                            virtnet_propertea1, virtnet_propertea2)
            self.print_and_inc()

    def test_02_db(self):
        """
        Load Cartesian combinatorial result from params into database
        """
        try:
            os.unlink(self.db_filename)
        except OSError:
            pass
        self.zero_counter()
        for fakevm in self.fakevm_generator():
            test_params = fakevm.get_params()
            virtnet = utils_net.DbNet(test_params, fakevm.name,
                                      self.db_filename, fakevm.instance)
            self.assert_(hasattr(virtnet, 'container_class'))
            self.assert_(hasattr(virtnet, 'mac_prefix'))
            self.assert_(not hasattr(virtnet, 'lock'))
            self.assert_(not hasattr(virtnet, 'db'))
            vm_name_params = test_params.object_params(fakevm.name)
            nic_name_list = vm_name_params.objects('nics')
            for nic_name in nic_name_list:
                # nic name is only in params scope
                nic_dict = {'nic_name': nic_name}
                nic_params = test_params.object_params(nic_name)
                # avoid processing unsupported properties
                proplist = list(virtnet.container_class().__all_slots__)
                # name was already set, remove from __slots__ list copy
                del proplist[proplist.index('nic_name')]
                for propertea in proplist:
                    nic_dict[propertea] = nic_params.get(propertea)
                virtnet.append(nic_dict)
            virtnet.update_db()
            # db shouldn't store empty items
            self.print_and_inc()

    def test_03_db(self):
        """
        Load from database created in test_02_db, verify data against params
        """
        # Verify on-disk data matches dummy data just written
        self.zero_counter()
        db = shelve.open(self.db_filename)
        db_keys = db.keys()
        self.assertEqual(len(db_keys), self.db_item_count)
        for key in db_keys:
            db_value = eval(db[key], {}, {})
            self.assert_(isinstance(db_value, list))
            self.assert_(len(db_value) > 0)
            self.assert_(isinstance(db_value[0], dict))
            for nic in db_value:
                mac = nic.get('mac')
                if mac:
                    # Another test already checked mac_is_valid behavior
                    self.assert_(utils_net.VirtIface.mac_is_valid(mac))
            self.print_and_inc()
        db.close()

    def test_04_VirtNet(self):
        """
        Populate database with max - 1 mac addresses
        """
        try:
            os.unlink(self.db_filename)
        except OSError:
            pass
        self.zero_counter(25)
        # setup() method already set LASTBYTE to '-1'
        for lastbyte in xrange(0, 0xFF):
            # test_07_VirtNet demands last byte in name and mac match
            vm_name = "vm%d" % lastbyte
            if lastbyte < 16:
                mac = "%s0%x" % (self.mac_prefix, lastbyte)
            else:
                mac = "%s%x" % (self.mac_prefix, lastbyte)
            params = utils_params.Params({
                "nics": "nic1",
                "vms": vm_name,
                "mac_nic1": mac,
            })
            virtnet = utils_net.VirtNet(params, vm_name,
                                        vm_name, self.db_filename)
            virtnet.mac_prefix = self.mac_prefix
            self.assertEqual(virtnet['nic1'].mac, mac)
            self.assertEqual(virtnet.get_mac_address(0), mac)
            # Confirm only lower-case macs are stored
            self.assertEqual(virtnet.get_mac_address(0).lower(),
                             virtnet.get_mac_address(0))
            self.assertEqual(virtnet.mac_list(), [mac])
            self.print_and_inc()

    def test_05_VirtNet(self):
        """
        Load max - 1 entries from db, overriding params.

        DEPENDS ON test_04_VirtNet running first
        """
        self.zero_counter(25)
        # second loop forces db load from disk
        # also confirming params merge with db data
        for lastbyte in xrange(0, 0xFF):
            vm_name = "vm%d" % lastbyte
            params = utils_params.Params({
                "nics": "nic1",
                "vms": vm_name
            })
            virtnet = utils_net.VirtNet(params, vm_name,
                                        vm_name, self.db_filename)
            if lastbyte < 16:
                mac = "%s0%x" % (self.mac_prefix, lastbyte)
            else:
                mac = "%s%x" % (self.mac_prefix, lastbyte)
            self.assertEqual(virtnet['nic1'].mac, mac)
            self.assertEqual(virtnet.get_mac_address(0), mac)
            self.print_and_inc()

    def test_06_VirtNet(self):
        """
        Generate last possibly mac and verify value.

        DEPENDS ON test_05_VirtNet running first
        """
        self.zero_counter(25)
        # test two nics, second mac generation should fail (pool exhausted)
        params = utils_params.Params({
            "nics": "nic1 nic2",
            "vms": "vm255"
        })
        virtnet = utils_net.VirtNet(params, 'vm255',
                                    'vm255', self.db_filename)
        virtnet.mac_prefix = self.mac_prefix
        self.assertRaises(AttributeError, virtnet.get_mac_address, 'nic1')
        mac = "%s%x" % (self.mac_prefix, 255)
        # This will grab the last available address
        # only try 300 times, guarantees LASTBYTE counter will loop once
        self.assertEqual(virtnet.generate_mac_address(0, 300), mac)
        # This will fail allocation
        self.assertRaises(utils_net.NetError,
                          virtnet.generate_mac_address, 1, 300)

    def test_07_VirtNet(self):
        """
        Release mac from beginning, midle, and end, re-generate + verify value
        """
        self.zero_counter(1)
        beginning_params = utils_params.Params({
            "nics": "nic1 nic2",
            "vms": "vm0"
        })
        middle_params = utils_params.Params({
            "nics": "nic1 nic2",
            "vms": "vm127"
        })
        end_params = utils_params.Params({
            "nics": "nic1 nic2",
            "vms": "vm255",
        })
        for params in (beginning_params, middle_params, end_params):
            vm_name = params['vms']
            virtnet = utils_net.VirtNet(params, vm_name,
                                        vm_name, self.db_filename)
            virtnet.mac_prefix = self.mac_prefix
            iface = virtnet['nic1']
            last_db_mac_byte = iface.mac_str_to_int_list(iface.mac)[-1]
            last_vm_name_byte = int(vm_name[2:])
            # Sequential generation from test_04_VirtNet guarantee
            self.assertEqual(last_db_mac_byte, last_vm_name_byte)
            # only try 300 times, guarantees LASTBYTE counter will loop once
            self.assertRaises(
                utils_net.NetError, virtnet.generate_mac_address, 1, 300)
            virtnet.free_mac_address(0)
            virtnet.free_mac_address(1)
            # generate new on nic1 to verify mac_index generator catches it
            # and to signify database updated after generation
            virtnet.generate_mac_address(1, 300)
            last_db_mac_byte = virtnet['nic2'].mac_str_to_int_list(
                virtnet['nic2'].mac)[-1]
            self.assertEqual(last_db_mac_byte, last_vm_name_byte)
            self.assertEqual(virtnet.get_mac_address(1), virtnet[1].mac)
            self.print_and_inc()

    def test_08_ifname(self):
        for fakevm in self.fakevm_generator():
            # only need to test kvm instance
            if fakevm.vm_type != 'qemu':
                continue
            test_params = fakevm.get_params()
            virtnet = utils_net.VirtNet(test_params,
                                        fakevm.name,
                                        fakevm.name)
            for virtnet_index in xrange(0, len(virtnet)):
                result = virtnet.generate_ifname(virtnet_index)
                self.assertEqual(result, virtnet[virtnet_index].ifname)
                # assume less than 10 nics
                self.assert_(len(result) < 11)
            if len(virtnet) == 2:
                break  # no need to test every possible combination

    def test_99_ifname(self):
        # cleanup
        try:
            os.unlink(self.db_filename)
        except OSError:
            pass


if __name__ == '__main__':
    unittest.main()
