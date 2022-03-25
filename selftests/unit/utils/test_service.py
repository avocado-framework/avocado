#  Copyright(c) 2013 Intel Corporation.
#
#  This program is free software; you can redistribute it and/or modify it
#  under the terms and conditions of the GNU General Public License,
#  version 2, as published by the Free Software Foundation.
#
#  This program is distributed in the hope it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
#  more details.
#
#  You should have received a copy of the GNU General Public License along with
#  this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin St - Fifth Floor, Boston, MA 02110-1301 USA.
#
#  The full GNU General Public License is included in this distribution in
#  the file called "COPYING".

import unittest.mock

from avocado.utils import service
from selftests.utils import setup_avocado_loggers

setup_avocado_loggers()


class TestMultipleInstances(unittest.TestCase):

    def test_different_runners(self):
        # Call 'set_target' on first runner
        runner1 = unittest.mock.Mock()
        runner1.return_value.stdout = 'systemd'
        service1 = service.service_manager(run=runner1)
        service1.set_target('foo_target')
        self.assertEqual(runner1.call_args[0][0],  # pylint: disable=E1136
                         'systemctl isolate foo_target')
        # Call 'start' on second runner
        runner2 = unittest.mock.Mock()
        runner2.return_value.stdout = 'init'
        service2 = service.service_manager(run=runner2)
        service2.start('foo_service')
        self.assertEqual(runner2.call_args[0][0],  # pylint: disable=E1136
                         'service foo_service start')


class TestSystemd(unittest.TestCase):

    def setUp(self):
        self.service_name = "fake_service"
        init_name = "systemd"
        command_generator = service._COMMAND_GENERATORS[init_name]
        self.service_command_generator = service._ServiceCommandGenerator(
            command_generator)

    def test_all_commands(self):
        # Test all commands except "set_target" which is tested elsewhere
        for cmd, _ in ((c, r) for (c, r) in
                       self.service_command_generator.commands if
                       c != "set_target"):
            ret = getattr(
                self.service_command_generator, cmd)(self.service_name)
            if cmd == "is_enabled":
                cmd = "is-enabled"
            if cmd == "reset_failed":
                cmd = "reset-failed"
            if cmd == "list":
                self.assertEqual(ret, ['systemctl', 'list-unit-files',
                                       '--type=service', '--no-pager',
                                       '--full'])
            else:
                self.assertEqual(ret, ["systemctl", cmd,
                                       f"{self.service_name}.service"])

    def test_set_target(self):
        ret = getattr(
            self.service_command_generator, "set_target")("multi-user.target")
        self.assertEqual(ret, ["systemctl", "isolate", "multi-user.target"])


class TestSysVInit(unittest.TestCase):

    def setUp(self):
        self.service_name = "fake_service"
        init_name = "init"
        command_generator = service._COMMAND_GENERATORS[init_name]
        self.service_command_generator = service._ServiceCommandGenerator(
            command_generator)

    def test_all_commands(self):
        command_name = "service"
        # Test all commands except "set_target" which is tested elsewhere
        for cmd, _ in ((c, r) for (c, r) in
                       self.service_command_generator.commands
                       if c != 'set_target'):
            ret = getattr(
                self.service_command_generator, cmd)(self.service_name)
            if cmd in ['set_target', 'reset_failed', 'mask', 'unmask']:
                exp = ['true']
            elif cmd == 'list':
                exp = ['chkconfig', '--list']
            else:
                if cmd == "is_enabled":
                    command_name = "chkconfig"
                    cmd = ""
                elif cmd == 'enable':
                    command_name = "chkconfig"
                    cmd = "on"
                elif cmd == 'disable':
                    command_name = "chkconfig"
                    cmd = "off"
                exp = [command_name, self.service_name, cmd]
            self.assertEqual(ret, exp)

    def test_set_target(self):
        ret = getattr(
            self.service_command_generator, "set_target")("multi-user.target")
        self.assertEqual(ret, ["telinit", "3"])


class TestSpecificServiceManager(unittest.TestCase):

    def setUp(self):
        self.run_mock = unittest.mock.Mock()
        self.init_name = "init"
        get_name_of_init_mock = unittest.mock.Mock(return_value="init")

        @unittest.mock.patch.object(service, "get_name_of_init",
                                    get_name_of_init_mock)
        def patch_service_command_generator():
            return service._auto_create_specific_service_command_generator()

        @unittest.mock.patch.object(service, "get_name_of_init",
                                    get_name_of_init_mock)
        def patch_service_result_parser():
            return service._auto_create_specific_service_result_parser()
        service_command_generator = patch_service_command_generator()
        service_result_parser = patch_service_result_parser()
        self.service_manager = service._SpecificServiceManager(
            "boot.lldpad", service_command_generator,
            service_result_parser, self.run_mock)

    def test_start(self):
        srv = "lldpad"
        self.service_manager.start()
        cmd = f"service boot.{srv} start"
        self.assertEqual(self.run_mock.call_args[0][0], cmd)  # pylint: disable=E1136

    def test_stop_with_args(self):
        srv = "lldpad"
        self.service_manager.stop(ignore_status=True)
        cmd = f"service boot.{srv} stop"
        self.assertEqual(self.run_mock.call_args[0][0], cmd)  # pylint: disable=E1136

    def test_list_is_not_present_in_SpecifcServiceManager(self):
        self.assertFalse(hasattr(self.service_manager, "list"))

    def test_set_target_is_not_present_in_SpecifcServiceManager(self):
        self.assertFalse(hasattr(self.service_manager, "set_target"))


def get_service_manager_from_init_and_run(init_name, run_mock):
    command_generator = service._COMMAND_GENERATORS[init_name]
    result_parser = service._RESULT_PARSERS[init_name]
    service_manager = service._SERVICE_MANAGERS[init_name]
    service_command_generator = service._ServiceCommandGenerator(
        command_generator)
    service_result_parser = service._ServiceResultParser(result_parser)
    return service_manager(service_command_generator, service_result_parser,
                           run_mock)


class TestSystemdServiceManager(unittest.TestCase):

    def setUp(self):
        self.run_mock = unittest.mock.Mock()
        self.init_name = "systemd"
        self.service_manager = get_service_manager_from_init_and_run(
            self.init_name,
            self.run_mock)

    def test_start(self):
        srv = "lldpad"
        self.service_manager.start(srv)
        cmd = f"systemctl start {srv}.service"
        self.assertEqual(self.run_mock.call_args[0][0], cmd)  # pylint: disable=E1136

    def test_list(self):
        list_result_mock = unittest.mock.Mock(
            exit_status=0,
            stdout_text="sshd.service enabled\n"
            "vsftpd.service disabled\n"
            "systemd-sysctl.service static\n")
        run_mock = unittest.mock.Mock(return_value=list_result_mock)
        service_manager = get_service_manager_from_init_and_run(self.init_name,
                                                                run_mock)
        list_result = service_manager.list(ignore_status=False)
        self.assertEqual(run_mock.call_args[0][0],  # pylint: disable=E1136
                         "systemctl list-unit-files --type=service "
                         "--no-pager --full")
        self.assertEqual(list_result, {'sshd': "enabled",
                                       'vsftpd': "disabled",
                                       'systemd-sysctl': "static"})

    def test_set_default_runlevel(self):
        runlevel = service.convert_sysv_runlevel(3)
        mktemp_mock = unittest.mock.Mock(return_value="temp_filename")
        symlink_mock = unittest.mock.Mock()
        rename_mock = unittest.mock.Mock()

        @unittest.mock.patch.object(service, "mkstemp", mktemp_mock)
        @unittest.mock.patch("os.symlink", symlink_mock)
        @unittest.mock.patch("os.rename", rename_mock)
        def _():
            self.service_manager.change_default_runlevel(runlevel)
            self.assertTrue(mktemp_mock.called)
            self.assertEqual(symlink_mock.call_args[0][0],  # pylint: disable=E1136
                             "/usr/lib/systemd/system/multi-user.target")
            self.assertEqual(rename_mock.call_args[0][1],  # pylint: disable=E1136
                             "/etc/systemd/system/default.target")
        _()

    def test_unknown_runlevel(self):
        self.assertRaises(ValueError,
                          service.convert_systemd_target_to_runlevel, "unknown")

    def test_runlevels(self):
        self.assertEqual(service.convert_sysv_runlevel(0), "poweroff.target")
        self.assertEqual(service.convert_sysv_runlevel(1), "rescue.target")
        self.assertEqual(service.convert_sysv_runlevel(2), "multi-user.target")
        self.assertEqual(service.convert_sysv_runlevel(5), "graphical.target")
        self.assertEqual(service.convert_sysv_runlevel(6), "reboot.target")


class TestSysVInitServiceManager(unittest.TestCase):

    def setUp(self):
        self.run_mock = unittest.mock.Mock()
        self.init_name = "init"
        self.service_manager = get_service_manager_from_init_and_run(
            self.init_name,
            self.run_mock)

    def test_start(self):
        srv = "lldpad"
        self.service_manager.start(srv)
        cmd = f"service {srv} start"
        self.assertEqual(self.run_mock.call_args[0][0], cmd)  # pylint: disable=E1136

    def test_list(self):
        list_result_mock = unittest.mock.Mock(
            exit_status=0,
            stdout_text="sshd             0:off   1:off   "
            "2:off   3:off   4:off   5:off   6:off\n"
            "vsftpd           0:off   1:off   2:off "
            "  3:off   4:off   5:on   6:off\n"
            "xinetd based services:\n"
            "        amanda:         off\n"
            "        chargen-dgram:  on\n")

        run_mock = unittest.mock.Mock(return_value=list_result_mock)
        service_manager = get_service_manager_from_init_and_run(self.init_name,
                                                                run_mock)
        list_result = service_manager.list(ignore_status=False)
        self.assertEqual(run_mock.call_args[0][0], "chkconfig --list")  # pylint: disable=E1136
        self.assertEqual(list_result,
                         {'sshd': {0: "off", 1: "off", 2: "off", 3: "off",
                                   4: "off", 5: "off", 6: "off"},
                          'vsftpd': {0: "off", 1: "off", 2: "off", 3: "off",
                                     4: "off", 5: "on", 6: "off"},
                          'xinetd': {'amanda': "off", 'chargen-dgram': "on"}})

    def test_enable(self):
        srv = "lldpad"
        self.service_manager.enable(srv)
        cmd = "chkconfig lldpad on"
        self.assertEqual(self.run_mock.call_args[0][0], cmd)  # pylint: disable=E1136

    def test_unknown_runlevel(self):
        self.assertRaises(ValueError,
                          service.convert_sysv_runlevel, "unknown")

    def test_runlevels(self):
        self.assertEqual(service.convert_systemd_target_to_runlevel(
            "poweroff.target"), '0')
        self.assertEqual(service.convert_systemd_target_to_runlevel(
            "rescue.target"), 's')
        self.assertEqual(service.convert_systemd_target_to_runlevel(
            "multi-user.target"), '3')
        self.assertEqual(service.convert_systemd_target_to_runlevel(
            "graphical.target"), '5')
        self.assertEqual(service.convert_systemd_target_to_runlevel(
            "reboot.target"), '6')


if __name__ == '__main__':
    unittest.main()
