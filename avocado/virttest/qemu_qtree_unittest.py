#!/usr/bin/python
"""
This is a unittest for qemu_qtree library.

:author: Lukas Doktor <ldoktor@redhat.com>
:copyright: 2012 Red Hat, Inc.
"""
__author__ = """Lukas Doktor (ldoktor@redhat.com)"""

import unittest

import common
from autotest.client.shared.test_utils import mock
import qemu_qtree

OFFSET_PER_LEVEL = qemu_qtree.OFFSET_PER_LEVEL


# Dummy classes and functions
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


def combine(first, second, offset):
    """ Add string line-by-line with offset*OFFSET_PER_LEVEL """
    out = first[:]
    offset = ' ' * OFFSET_PER_LEVEL * offset
    for line in second.splitlines():
        out += '\n' + offset + line
    return out

# Dummy variables
qtree_header = """bus: main-system-bus
  type System

"""

dev_ide_disk = """dev: piix3-ide, id ""
  bus-prop: addr = 01.1
  bus-prop: romfile = <null>
  bus-prop: rombar = 1
  bus-prop: multifunction = off
  bus-prop: command_serr_enable = on
  class IDE controller, addr 00:01.1, pci id 8086:7010 (sub 1af4:1100)
  bar 4: i/o at 0xc2a0 [0xc2af]
  bus: ide.0
    type IDE
    dev: ide-hd, id ""
      dev-prop: drive = ide0-hd0
      dev-prop: logical_block_size = 512
      dev-prop: physical_block_size = 512
      dev-prop: min_io_size = 0
      dev-prop: opt_io_size = 0
      dev-prop: bootindex = -1
      dev-prop: discard_granularity = 0
      dev-prop: ver = "1.0.50"
      dev-prop: serial = "QM00001"
      bus-prop: unit = 0"""

dev_usb_disk = """dev: ich9-usb-uhci1, id "usb1"
  dev-prop: masterbus = <null>
  dev-prop: firstport = 0
  bus-prop: addr = 04.0
  bus-prop: romfile = <null>
  bus-prop: rombar = 1
  bus-prop: multifunction = off
  bus-prop: command_serr_enable = on
  class USB controller, addr 00:04.0, pci id 8086:2934 (sub 1af4:1100)
  bar 4: i/o at 0xc280 [0xc29f]
  bus: usb1.0
    type USB
    dev: usb-hub, id ""
      bus-prop: port = <null>
      addr 0.3, port 2, speed 12, name QEMU USB Hub, attached
    dev: usb-tablet, id "usb-tablet1"
      bus-prop: port = <null>
      addr 0.4, port 2.1, speed 12, name QEMU USB Tablet, attached
    dev: usb-storage, id ""
      dev-prop: drive = <null>
      dev-prop: logical_block_size = 512
      dev-prop: physical_block_size = 512
      dev-prop: min_io_size = 0
      dev-prop: opt_io_size = 0
      dev-prop: bootindex = -1
      dev-prop: discard_granularity = 0
      dev-prop: serial = <null>
      dev-prop: removable = off
      bus-prop: port = <null>
      addr 0.2, port 1, speed 12, name QEMU USB MSD, attached
      bus: scsi.0
        type SCSI
        dev: scsi-disk, id ""
          dev-prop: drive = usb2.6
          dev-prop: logical_block_size = 512
          dev-prop: physical_block_size = 512
          dev-prop: min_io_size = 0
          dev-prop: opt_io_size = 0
          dev-prop: bootindex = -1
          dev-prop: discard_granularity = 0
          dev-prop: ver = "1.0.50"
          dev-prop: serial = <null>
          dev-prop: removable = off
          bus-prop: channel = 0
          bus-prop: scsi-id = 0
          bus-prop: lun = 0"""

dev_dummy_mmio = """dev: fw_cfg, id ""
  dev-prop: ctl_iobase = 0x510
  dev-prop: data_iobase = 0x511
  irq 0
  mmio ffffffffffffffff/0000000000000002
  mmio ffffffffffffffff/0000000000000001"""

info_block = {'ide0-hd0': {'removable': 0, 'io-status': 'ok',
                           'file': '/tmp/vl.UWzrkU',
                           'backing_file': '/dummy/directory/f16-64.qcow2',
                           'ro': 1, 'drv': 'qcow2', 'encrypted': 0, 'bps': 0,
                           'bps_rd': 0, 'bps_wr': 0, 'iops': 0, 'iops_rd': 0,
                           'iops_wr': 0},
              'usb2.6': {'removable': 0, 'io-status': 'ok',
                         'file': '/tmp/stg4.qcow2', 'ro': 0, 'drv': 'qcow2',
                         'encrypted': 0, 'bps': 0, 'bps_rd': 0, 'bps_wr': 0,
                         'iops': 0, 'iops_rd': 0, 'iops_wr': 0}}

guest_proc_scsi = """Attached devices:
Host: scsi4 Channel: 00 Id: 00 Lun: 00
  Vendor: QEMU     Model: QEMU HARDDISK    Rev: 1.0.
  Type:   Direct-Access                    ANSI  SCSI revision: 05"""

params = ParamsDict({'images': 'image1 stg4',
                     'drive_format': 'ide',
                     'drive_format_stg4': 'usb2',
                     'drive_index_image1': '0',
                     'drive_index_stg4': '6',
                     'image_format': 'qcow2',
                     'image_name': '/dummy/directory/f16-64',
                     'image_name_stg4': 'stg4',
                     'image_size': '10G',
                     'image_size_stg4': '1M',
                     'image_snapshot': 'yes',
                     'image_snapshot_stg4': 'no',
                     'image_readonly_image1': 'yes',
                     'cdroms': 'cdrom1'})


class QtreeContainerTest(unittest.TestCase):

    """ QtreeContainer tests """

    def test_qtree(self):
        """ Correct workflow """
        reference_nodes = [qemu_qtree.QtreeDisk, qemu_qtree.QtreeBus,
                           qemu_qtree.QtreeDev, qemu_qtree.QtreeDev,
                           qemu_qtree.QtreeDev, qemu_qtree.QtreeDisk,
                           qemu_qtree.QtreeBus, qemu_qtree.QtreeDev,
                           qemu_qtree.QtreeBus, qemu_qtree.QtreeDev,
                           qemu_qtree.QtreeDev, qemu_qtree.QtreeBus]

        info = qtree_header
        info = combine(info, dev_ide_disk, 1)
        info = combine(info, dev_usb_disk, 1)
        info = combine(info, dev_dummy_mmio, 1)
        info += "\n"

        qtree = qemu_qtree.QtreeContainer()
        qtree.parse_info_qtree(info)
        nodes = qtree.get_nodes()

        self.assertEqual(len(nodes), len(reference_nodes), ("Number of parsed "
                                                            "nodes is not equal to the number of qtree nodes. "
                                                            "%s != %s" % (len(nodes), len(reference_nodes))))

        for i in xrange(len(nodes)):
            self.assertTrue(isinstance(nodes[i], reference_nodes[i]),
                            ("Node %d should be class %s but is %s instead" %
                             (i, reference_nodes[i], type(reference_nodes))))

        tree = qtree.get_qtree()
        self.assertTrue(isinstance(tree.str_qtree(), str),
                        "qtree.str_qtree() returns nonstring output.")

        self.assertTrue(isinstance(str(tree), str),
                        "str(qtree) returns nonstring output.")

    def test_bad_qtree(self):
        """ Incorrect qtree """
        qtree = qemu_qtree.QtreeContainer()
        info = combine(qtree_header, "Very_bad_line", 1)
        self.assertRaises(ValueError, qtree.parse_info_qtree, info)


class QtreeDiskContainerTest(unittest.TestCase):

    """ QtreeDiskContainer tests """

    def setUp(self):
        # Get rid of logging errors
        def dumm(*args, **kvargs):
            pass
        self.god = mock.mock_god(ut=self)
        self.god.stub_with(qemu_qtree.logging, 'error', dumm)

        info = qtree_header
        info = combine(info, dev_ide_disk, 1)
        info = combine(info, dev_usb_disk, 1)
        info = combine(info, dev_dummy_mmio, 1)
        info += "\n"

        self.no_disks = 2

        self.qtree = qemu_qtree.QtreeContainer()
        self.qtree.parse_info_qtree(info)

        self.disks = qemu_qtree.QtreeDisksContainer(self.qtree.get_nodes())

    def tearDown(self):
        self.god.unstub_all()

    def test_check_params(self):
        """ Correct workflow """
        disks = self.disks
        self.assertEqual(len(self.disks.disks), self.no_disks)
        self.assertEqual(disks.parse_info_block(info_block), (0, 0))
        self.assertEqual(disks.generate_params(), 0)
        self.assertEqual(disks.check_disk_params(params), 2)
        self.assertEqual(disks.check_guests_proc_scsi(guest_proc_scsi),
                         (0, 0, 1, 0))
        # Check the full disk output (including params)
        for disk in disks.disks:
            self.assertTrue(isinstance(str(disk), str),
                            "str(disk) returns nonstring output.")

    def test_check_params_bad(self):
        """ Whole workflow with bad data """
        disks = self.disks
        # missing disk in info block
        _info_block = info_block.copy()
        _info_block.pop('ide0-hd0')
        # snapshot in info qtree but not in params
        _info_block['usb2.6']['file'] = 'none.qcow2'
        _info_block['usb2.6']['backing_file'] = '/tmp/stg4.qcow2'
        # additional disk in info block
        _info_block['missing_bad_disk1'] = {}
        # additional disk in params
        _params = ParamsDict(params)
        _params['images'] += ' bad_disk2'
        # Missing disk in proc_scsi
        _guest_proc_scsi = guest_proc_scsi.replace('Channel: 00',
                                                   'Channel: 01')
        # Ignored disk in proc_scsi
        _guest_proc_scsi += """
Host: scsi1 Channel: 00 Id: 00 Lun: 00
  Vendor: ATA      Model: QEMU HARDDISK    Rev: 1.0.
  Type:   Direct-Access                    ANSI  SCSI revision: 05"""

        self.assertEqual(disks.parse_info_block(_info_block), (1, 1))
        self.assertEqual(disks.generate_params(), 1)
        self.assertEqual(disks.check_disk_params(_params), 4)
        self.assertEqual(disks.check_guests_proc_scsi(_guest_proc_scsi),
                         (0, 1, 1, 0))


class KvmQtreeClassTest(unittest.TestCase):

    """ Additional tests for qemu_qtree classes """

    def test_qtree_bus_bus(self):
        """ Bus' child can't be Bus() """
        test = qemu_qtree.QtreeBus()
        self.assertRaises(qemu_qtree.IncompatibleTypeError,
                          test.add_child, qemu_qtree.QtreeBus())

    def test_qtree_dev_dev(self):
        """ Dev's child can't be Dev() """
        test = qemu_qtree.QtreeDev()
        self.assertRaises(qemu_qtree.IncompatibleTypeError,
                          test.add_child, qemu_qtree.QtreeDev())

    def test_qtree_disk_missing_filename(self):
        """ in info_block must contain info about file or backing_file """
        test = qemu_qtree.QtreeDisk()
        test.set_qtree({'something': 'something'})
        test.set_block_prop('prop', 'value')
        self.assertRaises(ValueError, test.generate_params)


if __name__ == "__main__":
    """ Run unittest """
    unittest.main()
