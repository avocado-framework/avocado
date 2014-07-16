import unittest

import common
from qemu_monitor import Monitor
import qemu_monitor


class MockMonitor(qemu_monitor.Monitor):

    """ Dummy class inherited from qemu_monitor.HumanMonitor """

    def __init__(self):     # pylint: disable=W0231
        pass

    def __del__(self):
        pass


class InfoNumaTests(unittest.TestCase):

    def testZeroNodes(self):
        d = "0 nodes\n"
        r = Monitor.parse_info_numa(d)
        self.assertEquals(r, [])

    def testTwoNodes(self):
        d = "2 nodes\n" + \
            "node 0 cpus: 0 2 4\n" + \
            "node 0 size: 12 MB\n" + \
            "node 1 cpus: 1 3 5\n" + \
            "node 1 size: 34 MB\n"
        r = Monitor.parse_info_numa(d)
        self.assertEquals(r, [(12, set([0, 2, 4])),
                              (34, set([1, 3, 5]))])


class InfoBlocks(unittest.TestCase):

    def testParseBlocks(self):
        info_1_4 = """ide0-hd0: removable=0 io-status=ok file=c.qcow2 backing_file=b.qcow2 backing_file_depth=2 ro=0 drv=qcow2 encrypted=0 bps=0 bps_rd=0 bps_wr=0 iops=0 iops_rd=0 iops_wr=0
scsi0-hd0: removable=0 io-status=ok file=a.qcow ro=1 drv=raw encrypted=0 bps=0 bps_rd=0 bps_wr=0 iops=0 iops_rd=0 iops_wr=0
scsi0-hd1: removable=0 io-status=ok file=enc.qcow2 ro=0 drv=qcow2 encrypted=1 bps=0 bps_rd=0 bps_wr=0 iops=0 iops_rd=0 iops_wr=0
ide1-cd0: removable=1 locked=0 tray-open=0 io-status=ok [not inserted]
floppy0: removable=1 locked=0 tray-open=0 [not inserted]
sd0: removable=1 locked=0 tray-open=0 [not inserted]"""
        info_1_5 = """ide0-hd0: c.qcow2 (qcow2)
    Backing file:     b.qcow2 (chain depth: 2)

scsi0-hd0: a.qcow (raw, read-only)

scsi0-hd1: enc.qcow2 (qcow2, encrypted)

ide1-cd0: [not inserted]
    Removable device: not locked, tray closed

floppy0: [not inserted]
    Removable device: not locked, tray closed

sd0: [not inserted]
    Removable device: not locked, tray closed"""
        info_qmp = [{"io-status": "ok", "device": "ide0-hd0", "locked":
                     False, "removable": False, "inserted": {"iops_rd": 0,
                                                             "iops_wr": 0, "ro": False, "backing_file_depth": 2,
                                                             "drv": "qcow2", "iops": 0, "bps_wr": 0, "backing_file":
                                                             "b.qcow2", "encrypted": False, "bps": 0, "bps_rd": 0,
                                                             "file": "c.qcow2", "encryption_key_missing": False},
                     "type": "unknown"}, {"io-status": "ok", "device":
                                          "scsi0-hd0", "locked": False, "removable": False,
                                          "inserted": {"iops_rd": 0, "iops_wr": 0, "ro": True,
                                                       "backing_file_depth": 0, "drv": "raw", "iops": 0,
                                                       "bps_wr": 0, "encrypted": False, "bps": 0, "bps_rd": 0,
                                                       "file": "a.qcow", "encryption_key_missing": False},
                                          "type": "unknown"}, {"io-status": "ok", "device":
                                                               "scsi0-hd1", "locked": False, "removable": False,
                                                               "inserted": {"iops_rd": 0, "iops_wr": 0, "ro": False,
                                                                            "backing_file_depth": 0, "drv": "qcow2", "iops": 0,
                                                                            "bps_wr": 0, "encrypted": True, "bps": 0, "bps_rd": 0,
                                                                            "file": "enc.qcow2", "encryption_key_missing": True},
                                                               "type": "unknown"}, {"io-status": "ok", "device":
                                                                                    "ide1-cd0", "locked": False, "removable": True,
                                                                                    "tray_open": False, "type": "unknown"}, {"device":
                                                                                                                             "floppy0", "locked": False, "removable": True,
                                                                                                                             "tray_open": False, "type": "unknown"}, {"device": "sd0",
                                                                                                                                                                      "locked": False, "removable": True, "tray_open": False,
                                                                                                                                                                      "type": "unknown"}]
        monitor = MockMonitor()

        # Test "info block" version 1.4
        monitor.info = lambda _what, _debug: info_1_4
        out1 = monitor.info_block()
        exp = {'sd0': {'tray-open': 0, 'locked': 0, 'not-inserted': 1,
                       'removable': 1},
               'ide0-hd0': {'bps_rd': 0, 'backing_file_depth': 2,
                            'removable': 0, 'encrypted': 0, 'bps_wr': 0,
                            'io-status': 'ok', 'drv': 'qcow2', 'bps': 0,
                            'iops': 0, 'file': 'c.qcow2', 'iops_rd': 0,
                            'ro': 0, 'backing_file': 'b.qcow2', 'iops_wr': 0},
               'floppy0': {'tray-open': 0, 'locked': 0, 'not-inserted': 1,
                           'removable': 1},
               'ide1-cd0': {'tray-open': 0, 'locked': 0, 'not-inserted': 1,
                            'io-status': 'ok', 'removable': 1},
               'scsi0-hd0': {'bps_rd': 0, 'removable': 0, 'encrypted': 0,
                             'bps_wr': 0, 'io-status': 'ok', 'drv': 'raw',
                             'bps': 0, 'iops': 0, 'file': 'a.qcow',
                             'iops_rd': 0, 'ro': 1, 'iops_wr': 0},
               'scsi0-hd1': {'bps_rd': 0, 'removable': 0, 'encrypted': 1,
                             'bps_wr': 0, 'io-status': 'ok', 'drv': 'qcow2',
                             'bps': 0, 'iops': 0, 'file': 'enc.qcow2',
                             'iops_rd': 0, 'ro': 0, 'iops_wr': 0}}
        assert out1 == exp, ("Info block of qemu 1.4 is parsed incorrectly\n%s"
                             "\n%s" % (out1, exp))

        # Test "info block" version 1.5
        monitor.info = lambda _what, _debug: info_1_5
        out2 = monitor.info_block()
        exp = {'sd0': {'not-inserted': 1, 'removable': 1},
               'ide0-hd0': {'backing_file_depth': 2, 'drv': 'qcow2',
                            'backing_file': 'b.qcow2', 'file': 'c.qcow2'},
               'floppy0': {'not-inserted': 1, 'removable': 1},
               'ide1-cd0': {'not-inserted': 1, 'removable': 1},
               'scsi0-hd0': {'drv': 'raw', 'ro': 1, 'file': 'a.qcow'},
               'scsi0-hd1': {'encrypted': 1, 'drv': 'qcow2',
                             'file': 'enc.qcow2'}}
        assert out2 == exp, ("Info block of qemu 1.5 is parsed incorrectly\n%s"
                             "\n%s" % (out2, exp))

        # verify, that booth representation gives the same results
        # (qemu-1.5 is less informative so not all params are checked)
        for name, params in out2.iteritems():
            assert name in out1, ("missing disk '%s' in info-1.5\n%s\n%s"
                                  % (name, out2, out1))
            for key, value in params.iteritems():
                assert out1[name].get(key, 0) == value, ("value of disk %s "
                                                         "mismatch in info-1.5 %s=%s (%s)\n%s\n%s"
                                                         % (name, key, value, out1[
                                                             name].get(key, 0),
                                                            out2, out1))

        # Test "query-block" qmp version
        monitor.info = lambda _what, _debug: info_qmp
        out3 = monitor.info_block()
        exp = {'sd0': {'type': 'unknown', 'tray_open': False,
                       'not-inserted': True, 'removable': True,
                       'locked': False},
               'ide0-hd0': {'bps_rd': 0, 'backing_file_depth': 2,
                            'removable': False, 'type': 'unknown',
                            'encrypted': False, 'bps_wr': 0, 'locked': False,
                            'drv': 'qcow2', 'bps': 0, 'iops': 0,
                            'io-status': 'ok', 'file': 'c.qcow2',
                            'iops_rd': 0, 'encryption_key_missing': False,
                            'ro': False, 'backing_file': 'b.qcow2',
                            'iops_wr': 0},
               'floppy0': {'type': 'unknown', 'tray_open': False,
                           'not-inserted': True, 'removable': True,
                           'locked': False},
               'ide1-cd0': {'locked': False, 'tray_open': False,
                            'io-status': 'ok', 'removable': True,
                            'not-inserted': True, 'type': 'unknown'},
               'scsi0-hd0': {'bps_rd': 0, 'backing_file_depth': 0,
                             'removable': False, 'encrypted': False,
                             'bps_wr': 0, 'locked': False, 'drv': 'raw',
                             'bps': 0, 'iops': 0, 'io-status': 'ok',
                             'file': 'a.qcow', 'iops_rd': 0,
                             'encryption_key_missing': False, 'ro': True,
                             'type': 'unknown', 'iops_wr': 0},
               'scsi0-hd1': {'bps_rd': 0, 'backing_file_depth': 0,
                             'removable': False, 'encrypted': True,
                             'bps_wr': 0, 'locked': False, 'drv': 'qcow2',
                             'bps': 0, 'iops': 0, 'io-status': 'ok',
                             'file': 'enc.qcow2', 'iops_rd': 0,
                             'encryption_key_missing': True, 'ro': False,
                             'type': 'unknown', 'iops_wr': 0}}
        assert out3 == exp, ("QMP query-block of qemu is parsed incorrectly\n"
                             "%s\n%s" % (out3, exp))

        # verify, that booth representation gives the same results
        # (qemu-1.4 is less informative so not all params are checked)
        for name, params in out1.iteritems():
            assert name in out3, ("missing disk '%s' in info-1.5\n%s\n%s"
                                  % (name, out1, out3))
            for key, value in params.iteritems():
                assert out3[name].get(key, 0) == value, ("value of disk %s "
                                                         "mismatch in QMP version %s=%s (%s)\n%s\n%s"
                                                         % (name, key, value, out3[
                                                             name].get(key, 0),
                                                            out1, out3))


if __name__ == "__main__":
    unittest.main()
