#!/usr/bin/python
import unittest
import os

import common
from autotest.client.shared.test_utils import mock
from autotest.client import os_dep
from autotest.client.shared import utils

from virttest import nfs
from virttest import utils_misc

from virttest.staging import service


class FakeService(object):

    def __init__(self, service_name):
        self.fake_cmds = [{"cmd": "status", "stdout": True},
                          {"cmd": "restart", "stdout": ""}]

    def get_stdout(self, cmd):
        for fake_cmd in self.fake_cmds:
            if fake_cmd['cmd'] == cmd:
                return fake_cmd['stdout']
        raise ValueError("Could not locate locate '%s' on fake cmd db" % cmd)

    def status(self):
        return self.get_stdout("status")

    def restart(self):
        return self.get_stdout("restart")


class nfs_test(unittest.TestCase):

    def setup_stubs_init(self):
        os_dep.command.expect_call("mount")
        os_dep.command.expect_call("service")
        os_dep.command.expect_call("exportfs")
        service.Factory.create_service.expect_call("nfs").and_return(
            FakeService("nfs"))
        mount_src = self.nfs_params.get("nfs_mount_src")
        export_dir = (self.nfs_params.get("export_dir")
                      or mount_src.split(":")[-1])
        export_ip = self.nfs_params.get("export_ip", "*")
        export_options = self.nfs_params.get("export_options", "").strip()
        nfs.Exportfs.expect_new(export_dir, export_ip, export_options)

    def setup_stubs_setup(self, nfs_obj):
        os.makedirs.expect_call(nfs_obj.export_dir)
        nfs_obj.exportfs.export.expect_call()
        os.makedirs.expect_call(nfs_obj.mount_dir)
        utils_misc.mount.expect_call(nfs_obj.mount_src, nfs_obj.mount_dir,
                                     "nfs", perm=nfs_obj.mount_options)

    def setup_stubs_is_mounted(self, nfs_obj):
        utils_misc.is_mounted.expect_call(nfs_obj.mount_src,
                                          nfs_obj.mount_dir,
                                          "nfs").and_return(True)

    def setup_stubs_cleanup(self, nfs_obj):
        utils_misc.umount.expect_call(nfs_obj.mount_src,
                                      nfs_obj.mount_dir,
                                      "nfs")
        nfs_obj.exportfs.reset_export.expect_call()

    def setUp(self):
        self.nfs_params = {"nfs_mount_dir": "/mnt/nfstest",
                           "nfs_mount_options": "rw",
                           "nfs_mount_src": "127.0.0.1:/mnt/nfssrc",
                           "setup_local_nfs": "yes",
                           "export_options": "rw,no_root_squash"}
        self.god = mock.mock_god()
        self.god.stub_function(os_dep, "command")
        self.god.stub_function(utils, "system")
        self.god.stub_function(utils, "system_output")
        self.god.stub_function(os.path, "isfile")
        self.god.stub_function(os, "makedirs")
        self.god.stub_function(utils_misc, "is_mounted")
        self.god.stub_function(utils_misc, "mount")
        self.god.stub_function(utils_misc, "umount")
        self.god.stub_function(service.Factory, "create_service")
        attr = getattr(nfs, "Exportfs")
        setattr(attr, "already_exported", False)
        mock_class = self.god.create_mock_class_obj(attr, "Exportfs")
        self.god.stub_with(nfs, "Exportfs", mock_class)

    def tearDown(self):
        self.god.unstub_all()

    def test_nfs_setup(self):
        self.setup_stubs_init()
        nfs_local = nfs.Nfs(self.nfs_params)
        self.setup_stubs_setup(nfs_local)
        nfs_local.setup()
        self.setup_stubs_is_mounted(nfs_local)
        self.assertTrue(nfs_local.is_mounted())
        self.setup_stubs_cleanup(nfs_local)
        nfs_local.cleanup()
        self.god.check_playback()


if __name__ == "__main__":
    unittest.main()
