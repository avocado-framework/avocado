import unittest.mock

from avocado.utils.network import common
from avocado.utils.network import exceptions as nw_exceptions
from avocado.utils.network import hosts, interfaces, ports

try:
    import netifaces

    HAS_NETIFACES = True
except ImportError:
    HAS_NETIFACES = False


class PortTrackerTest(unittest.TestCase):
    def test_register_port(self):
        tracker = ports.PortTracker()
        ports.is_port_free = unittest.mock.MagicMock(return_value=True)
        self.assertNotIn(22, tracker.retained_ports)
        tracker.register_port(22)
        ports.is_port_free.assert_called_once_with(22, tracker.address)
        self.assertIn(22, tracker.retained_ports)

    def test_register_port_in_use(self):
        tracker = ports.PortTracker()
        ports.is_port_free = unittest.mock.MagicMock(return_value=False)
        with self.assertRaises(ValueError):
            tracker.register_port(22)
        ports.is_port_free.assert_called_once_with(22, tracker.address)

    def test_register_port_retained(self):
        tracker = ports.PortTracker()
        tracker.retained_ports = [22]
        with self.assertRaises(ValueError):
            tracker.register_port(22)

    def test_release_port(self):
        tracker = ports.PortTracker()
        tracker.retained_ports = [22]
        tracker.release_port(22)
        self.assertNotIn(22, tracker.retained_ports)

    def test_release_port_does_not_poke_system(self):
        tracker = ports.PortTracker()
        tracker.release_port = unittest.mock.MagicMock()
        ports.is_port_free = unittest.mock.MagicMock()
        tracker.release_port(22)
        tracker.release_port.assert_called_once_with(22)
        ports.is_port_free.assert_not_called()

    def test_find_free_port_from_tracker(self):
        tracker = ports.PortTracker()
        tracker._reset_retained_ports()
        ports.is_port_free = unittest.mock.MagicMock(return_value=True)
        port = tracker.find_free_port()
        self.assertEqual(port, tracker.start_port)
        self.assertIn(port, tracker.retained_ports)
        ports.is_port_free.assert_called_once_with(port, tracker.address)

    def test_find_free_port_from_tracker_with_start_port(self):
        tracker = ports.PortTracker()
        tracker._reset_retained_ports()
        ports.is_port_free = unittest.mock.MagicMock(return_value=True)
        port = tracker.find_free_port(start_port=6000)
        self.assertEqual(port, 6000)
        self.assertIn(port, tracker.retained_ports)

    def test_find_free_port_from_tracker_increments(self):
        tracker = ports.PortTracker()
        tracker._reset_retained_ports()
        tracker.retained_ports = [5000]
        ports.is_port_free = unittest.mock.MagicMock(return_value=True)
        port = tracker.find_free_port()
        self.assertEqual(port, 5001)
        self.assertIn(5001, tracker.retained_ports)
        ports.is_port_free.assert_called_with(5001, tracker.address)

    def test_borg_pattern(self):
        tracker1 = ports.PortTracker()
        tracker1._reset_retained_ports()
        tracker1.retained_ports.append(1234)
        tracker2 = ports.PortTracker()
        self.assertIn(1234, tracker2.retained_ports)
        tracker2.retained_ports.remove(1234)
        self.assertNotIn(1234, tracker1.retained_ports)
        tracker1._reset_retained_ports()

    def test_str(self):
        tracker = ports.PortTracker()
        tracker._reset_retained_ports()
        tracker.retained_ports.append(1234)
        self.assertEqual(str(tracker), "Ports tracked: [1234]")
        tracker._reset_retained_ports()


def get_all_local_addrs():
    """
    Returns all ipv4/ipv6 addresses that are associated with this machine
    """
    ipv4_addrs = []
    ipv6_addrs = []
    for interface in netifaces.interfaces():
        ifaddresses = netifaces.ifaddresses(interface)
        ipv4_addrs += [_["addr"] for _ in ifaddresses.get(netifaces.AF_INET, [])]
        ipv6_addrs += [_["addr"] for _ in ifaddresses.get(netifaces.AF_INET6, [])]
    if ipv4_addrs:
        ipv4_addrs += ["localhost", ""]
    if ipv6_addrs:
        ipv6_addrs += ["localhost", ""]
    return ipv4_addrs, ipv6_addrs


class PortsTest(unittest.TestCase):
    def test_is_port_available(self):
        port = ports.find_free_port(sequent=False)
        result = ports.is_port_available(port, "localhost")
        self.assertTrue(result)

    @unittest.mock.patch("socket.socket")
    def test_is_port_available_os_error(self, mock_socket):
        mock_socket.return_value.__enter__.return_value.bind.side_effect = OSError
        self.assertFalse(ports.is_port_available(22, "localhost"))

    @unittest.mock.patch("socket.socket")
    def test_is_port_available_permission_error(self, mock_socket):
        mock_socket.return_value.__enter__.return_value.bind.side_effect = (
            PermissionError
        )
        self.assertFalse(ports.is_port_available(22, "localhost"))

    def test_is_port_free_deprecation_warning(self):
        with self.assertWarns(DeprecationWarning):
            with unittest.mock.patch(
                "avocado.utils.network.ports.is_port_available"
            ) as mock_is_port_available:
                ports.is_port_free(22, "localhost")
                mock_is_port_available.assert_called_once_with(22, "localhost")

    def test_find_free_port(self):
        port = ports.find_free_port(sequent=False)
        self.assertEqual(type(port), int)

    @unittest.mock.patch("avocado.utils.network.ports.is_port_available")
    def test_find_free_port_not_found(self, mock_is_port_available):
        mock_is_port_available.return_value = False
        port = ports.find_free_port()
        self.assertIsNone(port)

    def test_find_free_ports(self):
        port = ports.find_free_ports(1000, 2000, 10)
        self.assertEqual(type(port), list)


class CommonTest(unittest.TestCase):
    def test_run_command_local(self):
        host = unittest.mock.MagicMock()
        host.__class__.__name__ = "LocalHost"
        with unittest.mock.patch(
            "avocado.utils.process.system_output"
        ) as mock_system_output:
            mock_system_output.return_value = b"output"
            output = common.run_command("command", host)
            self.assertEqual(output, "output")
            mock_system_output.assert_called_once_with("command", sudo=False)

    def test_run_command_remote(self):
        host = unittest.mock.MagicMock()
        host.__class__.__name__ = "RemoteHost"
        host.remote_session.cmd.return_value.stdout = b"output"
        output = common.run_command("command", host)
        self.assertEqual(output, "output")
        host.remote_session.cmd.assert_called_once_with("command")

    def test_run_command_remote_sudo(self):
        host = unittest.mock.MagicMock()
        host.__class__.__name__ = "RemoteHost"
        host.remote_session.cmd.return_value.stdout = b"output"
        output = common.run_command("command", host, sudo=True)
        self.assertEqual(output, "output")
        host.remote_session.cmd.assert_called_once_with("sudo command")


class HostsTest(unittest.TestCase):
    def test_host_instantiation(self):
        with self.assertRaises(TypeError):
            hosts.Host(host="localhost")

    @unittest.mock.patch("avocado.utils.network.hosts.run_command")
    def test_get_interfaces(self, mock_run_command):
        mock_run_command.return_value = "eth0 eth1"
        local_host = hosts.LocalHost()
        ifaces = local_host.interfaces
        self.assertEqual(len(ifaces), 2)
        self.assertEqual(ifaces[0].name, "eth0")
        self.assertEqual(ifaces[1].name, "eth1")
        mock_run_command.assert_called_once_with("ls /sys/class/net", local_host)

    @unittest.mock.patch("avocado.utils.network.hosts.run_command")
    def test_get_interfaces_with_bonding_masters(self, mock_run_command):
        mock_run_command.return_value = "eth0 eth1 bonding_masters"
        local_host = hosts.LocalHost()
        ifaces = local_host.interfaces
        self.assertEqual(len(ifaces), 2)
        self.assertEqual(ifaces[0].name, "eth0")
        self.assertEqual(ifaces[1].name, "eth1")

    @unittest.mock.patch("avocado.utils.network.hosts.run_command")
    def test_get_interfaces_exception(self, mock_run_command):
        mock_run_command.side_effect = Exception("Boom!")
        local_host = hosts.LocalHost()
        with self.assertRaises(nw_exceptions.NWException):
            local_host.interfaces  # pylint: disable=pointless-statement

    def test_get_interface_by_ipaddr(self):
        local_host = hosts.LocalHost()
        with unittest.mock.patch.object(
            hosts.Host,
            "interfaces",
            new_callable=unittest.mock.PropertyMock,
        ) as mock_interfaces:
            mock_iface = unittest.mock.MagicMock()
            mock_iface.get_ipaddrs.return_value = ["192.168.1.1"]
            mock_interfaces.return_value = [mock_iface]
            iface = local_host.get_interface_by_ipaddr("192.168.1.1")
            self.assertEqual(iface, mock_iface)
            iface = local_host.get_interface_by_ipaddr("192.168.1.2")
            self.assertIsNone(iface)

    def test_get_interface_by_hwaddr(self):
        local_host = hosts.LocalHost()
        with unittest.mock.patch.object(
            hosts.Host,
            "interfaces",
            new_callable=unittest.mock.PropertyMock,
        ) as mock_interfaces:
            mock_iface = unittest.mock.MagicMock()
            mock_iface.get_hwaddr.return_value = "00:11:22:33:44:55"
            mock_interfaces.return_value = [mock_iface]
            iface = local_host.get_interface_by_hwaddr("00:11:22:33:44:55")
            self.assertEqual(iface, mock_iface)
            iface = local_host.get_interface_by_hwaddr("00:11:22:33:44:66")
            self.assertIsNone(iface)

    @unittest.mock.patch("avocado.utils.network.hosts.run_command")
    def test_get_all_hwaddr(self, mock_run_command):
        mock_run_command.return_value = '[{"address": "00:11:22:33:44:55"}]'
        local_host = hosts.LocalHost()
        hwaddrs = local_host.get_all_hwaddr()
        self.assertEqual(hwaddrs, ["00:11:22:33:44:55"])

    @unittest.mock.patch("avocado.utils.network.hosts.run_command")
    def test_get_all_hwaddr_exception(self, mock_run_command):
        mock_run_command.return_value = "invalid json"
        local_host = hosts.LocalHost()
        with self.assertRaises(nw_exceptions.NWException):
            local_host.get_all_hwaddr()

    def test_validate_mac_addr(self):
        self.assertTrue(hosts.Host.validate_mac_addr("00:11:22:33:44:55"))
        self.assertFalse(hosts.Host.validate_mac_addr("00-11-22-33-44-55"))
        self.assertFalse(hosts.Host.validate_mac_addr(None))
        self.assertFalse(hosts.Host.validate_mac_addr("00:11:22:33:44:5g"))

    @unittest.mock.patch("avocado.utils.network.hosts.run_command")
    def test_get_default_route_interface(self, mock_run_command):
        mock_run_command.return_value = '[{"dev": "eth0"}]'
        local_host = hosts.LocalHost()
        ifaces = local_host.get_default_route_interface()
        self.assertEqual(ifaces, ["eth0"])

    @unittest.mock.patch("avocado.utils.network.hosts.run_command")
    def test_get_default_route_interface_exception(self, mock_run_command):
        mock_run_command.return_value = "invalid json"
        local_host = hosts.LocalHost()
        with self.assertRaises(nw_exceptions.NWException):
            local_host.get_default_route_interface()

    @unittest.mock.patch("avocado.utils.network.hosts.Session")
    def test_remote_host(self, mock_session):
        mock_session_instance = mock_session.return_value
        mock_session_instance.connect.return_value = True
        remote_host = hosts.RemoteHost(
            host="remote", username="user", password="password"
        )
        self.assertEqual(remote_host.remote_session, mock_session_instance)

    @unittest.mock.patch("avocado.utils.network.hosts.Session")
    def test_remote_host_with_statement(self, mock_session):
        mock_session_instance = mock_session.return_value
        mock_session_instance.connect.return_value = True
        with hosts.RemoteHost(
            host="remote", username="user", password="password"
        ) as remote_host:
            self.assertEqual(remote_host.remote_session, mock_session_instance)
        mock_session_instance.quit.assert_called_once()

    @unittest.mock.patch("avocado.utils.network.hosts.Session")
    def test_remote_host_connect_fail(self, mock_session):
        mock_session_instance = mock_session.return_value
        mock_session_instance.connect.return_value = False
        with self.assertRaises(nw_exceptions.NWException):
            hosts.RemoteHost(host="remote", username="user", password="password")

    @unittest.mock.patch("avocado.utils.network.hosts.Session")
    def test_remote_host_with_statement_already_connected(self, mock_session):
        mock_session_instance = mock_session.return_value
        mock_session_instance.connect.return_value = True
        remote_host = hosts.RemoteHost(
            host="remote", username="user", password="password"
        )
        with remote_host:
            pass
        mock_session_instance.quit.assert_called_once()


class InterfacesTest(unittest.TestCase):
    def setUp(self):
        self.host = unittest.mock.MagicMock()
        self.interface = interfaces.NetworkInterface("eth0", self.host)

    @unittest.mock.patch("avocado.utils.network.interfaces.distro_detect")
    def test_config_filename(self, mock_distro_detect):
        distro_mock = unittest.mock.MagicMock()
        mock_distro_detect.return_value = distro_mock
        distro_mock.name = "rhel"
        self.interface.distro_is_rhel9_or_later = True
        self.assertEqual(
            self.interface.config_filename,
            "/etc/NetworkManager/system-connections/eth0.nmconnection",
        )
        self.interface.distro_is_rhel9_or_later = False
        self.assertEqual(
            self.interface.config_filename, "/etc/sysconfig/network-scripts/ifcfg-eth0"
        )

    @unittest.mock.patch("avocado.utils.network.interfaces.distro_detect")
    def test_config_filename_suse(self, mock_distro_detect):
        distro_mock = unittest.mock.MagicMock()
        mock_distro_detect.return_value = distro_mock
        distro_mock.name = "SuSE"
        self.interface.distro_is_suse16_or_later = True
        self.assertEqual(
            self.interface.config_filename,
            "/etc/NetworkManager/system-connections/eth0.nmconnection",
        )
        self.interface.distro_is_suse16_or_later = False
        self.assertEqual(
            self.interface.config_filename, "/etc/sysconfig/network/ifcfg-eth0"
        )

    @unittest.mock.patch("avocado.utils.network.interfaces.distro_detect")
    def test_config_filename_unsupported(self, mock_distro_detect):
        distro_mock = unittest.mock.MagicMock()
        mock_distro_detect.return_value = distro_mock
        distro_mock.name = "unknown"
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.config_filename  # pylint: disable=pointless-statement

    @unittest.mock.patch("avocado.utils.network.interfaces.distro_detect")
    def test_slave_config_filename(self, mock_distro_detect):
        self.interface.distro_is_rhel9_or_later = True
        distro_mock = unittest.mock.MagicMock()
        mock_distro_detect.return_value = distro_mock
        distro_mock.name = "rhel"
        with unittest.mock.patch.object(
            self.interface,
            "_get_bondinterface_details",
            return_value={"slaves": ["eth1", "eth2"]},
        ):
            self.assertEqual(
                self.interface.slave_config_filename,
                [
                    "/etc/NetworkManager/system-connections/eth1.nmconnection",
                    "/etc/NetworkManager/system-connections/eth2.nmconnection",
                ],
            )

    def test_slave_config_filename_exception(self):
        with unittest.mock.patch.object(
            self.interface,
            "_get_bondinterface_details",
            side_effect=nw_exceptions.NWException,
        ):
            self.assertIsNone(self.interface.slave_config_filename)

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_get_interface_details(self, mock_run_command):
        mock_run_command.return_value = '[{"ifname": "eth0", "mtu": 1500}]'
        details = self.interface._get_interface_details()
        self.assertEqual(details, {"ifname": "eth0", "mtu": 1500})

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_get_interface_details_not_found(self, mock_run_command):
        mock_run_command.return_value = '[{"ifname": "eth1", "mtu": 1500}]'
        with self.assertRaises(nw_exceptions.NWException):
            self.interface._get_interface_details()

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_get_interface_details_invalid_json(self, mock_run_command):
        mock_run_command.return_value = "invalid json"
        with self.assertRaises(nw_exceptions.NWException):
            self.interface._get_interface_details()

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_set_hwaddr(self, mock_run_command):
        self.interface.set_hwaddr("00:11:22:33:44:55")
        mock_run_command.assert_called_once_with(
            "ip link set dev eth0 address 00:11:22:33:44:55", self.host, sudo=True
        )

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_set_hwaddr_exception(self, mock_run_command):
        mock_run_command.side_effect = Exception("Boom!")
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.set_hwaddr("00:11:22:33:44:55")

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_bring_up_down(self, mock_run_command):
        self.interface.bring_up()
        mock_run_command.assert_called_with("ip link set eth0 up", self.host, sudo=True)
        self.interface.bring_down()
        mock_run_command.assert_called_with(
            "ip link set eth0 down", self.host, sudo=True
        )

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_bring_down_exception(self, mock_run_command):
        mock_run_command.side_effect = Exception("Boom!")
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.bring_down()

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_bring_up_exception(self, mock_run_command):
        mock_run_command.side_effect = Exception("Boom!")
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.bring_up()

    def test_get_ipaddrs(self):
        with unittest.mock.patch.object(
            self.interface, "_get_interface_details"
        ) as mock_get_details:
            mock_get_details.return_value = {"addr_info": [{"local": "192.168.1.1"}]}
            addrs = self.interface.get_ipaddrs(version=4)
            self.assertEqual(addrs, ["192.168.1.1"])

    def test_get_ipaddrs_no_addr_info(self):
        with unittest.mock.patch.object(
            self.interface, "_get_interface_details"
        ) as mock_get_details:
            mock_get_details.return_value = {}
            addrs = self.interface.get_ipaddrs(version=4)
            self.assertEqual(addrs, [])

    def test_get_ipaddrs_exception(self):
        with unittest.mock.patch.object(
            self.interface,
            "_get_interface_details",
            side_effect=nw_exceptions.NWException,
        ):
            addrs = self.interface.get_ipaddrs(version=4)
            self.assertEqual(addrs, [])

    def test_get_ipaddrs_invalid_version(self):
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.get_ipaddrs(version=5)

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_get_hwaddr(self, mock_run_command):
        mock_run_command.return_value = "00:11:22:33:44:55"
        hwaddr = self.interface.get_hwaddr()
        self.assertEqual(hwaddr, "00:11:22:33:44:55")

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_get_hwaddr_exception(self, mock_run_command):
        mock_run_command.side_effect = Exception("Boom!")
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.get_hwaddr()

    def test_get_mtu(self):
        with unittest.mock.patch.object(
            self.interface, "_get_interface_details"
        ) as mock_get_details:
            mock_get_details.return_value = {"mtu": 1500}
            mtu = self.interface.get_mtu()
            self.assertEqual(mtu, 1500)

    def test_get_mtu_exception(self):
        with unittest.mock.patch.object(
            self.interface,
            "_get_interface_details",
            side_effect=nw_exceptions.NWException,
        ):
            with self.assertRaises(nw_exceptions.NWException):
                self.interface.get_mtu()

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_ping_check(self, mock_run_command):
        self.interface.ping_check("192.168.1.2")
        mock_run_command.assert_called_once_with(
            "ping -I eth0 192.168.1.2 -c 2", self.host
        )

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_ping_check_with_options(self, mock_run_command):
        self.interface.ping_check("192.168.1.2", options="-f")
        mock_run_command.assert_called_once_with(
            "ping -I eth0 192.168.1.2 -c 2 -f", self.host
        )

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_ping_check_exception(self, mock_run_command):
        mock_run_command.side_effect = Exception("Boom!")
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.ping_check("192.168.1.2")

    @unittest.mock.patch("avocado.utils.network.interfaces.wait_for")
    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_set_mtu(self, mock_run_command, mock_wait_for):
        with unittest.mock.patch.object(
            self.interface, "get_mtu", return_value=1500
        ), unittest.mock.patch.object(self.interface, "is_link_up", return_value=True):
            self.interface.set_mtu(1500)
        mock_run_command.assert_called_once_with(
            "ip link set eth0 mtu 1500", self.host, sudo=True
        )
        mock_wait_for.assert_called_once()

    @unittest.mock.patch("avocado.utils.network.interfaces.wait_for")
    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_set_mtu_exception(self, mock_run_command, mock_wait_for):
        with unittest.mock.patch.object(
            self.interface, "get_mtu", return_value=1200
        ), unittest.mock.patch.object(self.interface, "is_link_up", return_value=True):
            with self.assertRaises(nw_exceptions.NWException):
                self.interface.set_mtu(1500)
        mock_run_command.assert_called_once_with(
            "ip link set eth0 mtu 1500", self.host, sudo=True
        )
        mock_wait_for.assert_called_once()

    def test_validate_ipv4_format(self):
        self.assertTrue(interfaces.NetworkInterface.validate_ipv4_format("192.168.1.1"))
        self.assertFalse(
            interfaces.NetworkInterface.validate_ipv4_format("192.168.1.256")
        )

    def test_validate_ipv4_netmask_format(self):
        self.assertTrue(
            interfaces.NetworkInterface.validate_ipv4_netmask_format("255.255.255.0")
        )
        self.assertFalse(
            interfaces.NetworkInterface.validate_ipv4_netmask_format("255.255.0.255")
        )

    def test_validate_ipv4_netmask_format_invalid_length(self):
        self.assertFalse(
            interfaces.NetworkInterface.validate_ipv4_netmask_format(
                "255.255.255.255.255"
            )
        )

    def test_validate_ipv4_netmask_format_invalid_octet(self):
        self.assertFalse(
            interfaces.NetworkInterface.validate_ipv4_netmask_format("255.255.256.0")
        )

    def test_validate_ipv4_netmask_format_invalid_first_bit(self):
        self.assertFalse(
            interfaces.NetworkInterface.validate_ipv4_netmask_format("0.255.255.0")
        )

    def test_netmask_to_cidr(self):
        self.assertEqual(
            interfaces.NetworkInterface.netmask_to_cidr("255.255.255.0"), 24
        )

    @unittest.mock.patch("avocado.utils.network.interfaces.distro_detect")
    def test_config_file_path(self, mock_distro_detect):
        distro_mock = unittest.mock.MagicMock()
        mock_distro_detect.return_value = distro_mock
        distro_mock.name = "rhel"
        self.interface.distro_is_rhel9_or_later = True
        self.assertEqual(
            self.interface.config_file_path,
            "/etc/NetworkManager/system-connections",
        )
        self.interface.distro_is_rhel9_or_later = False
        self.assertEqual(
            self.interface.config_file_path, "/etc/sysconfig/network-scripts"
        )
        distro_mock.name = "SuSE"
        self.interface.distro_is_suse16_or_later = True
        self.assertEqual(
            self.interface.config_file_path,
            "/etc/NetworkManager/system-connections",
        )
        self.interface.distro_is_suse16_or_later = False
        self.assertEqual(self.interface.config_file_path, "/etc/sysconfig/network")
        distro_mock.name = "unknown"
        self.assertIsNone(self.interface.config_file_path)

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_add_ipaddr(self, mock_run_command):
        self.interface.add_ipaddr("192.168.1.1", "255.255.255.0")
        mock_run_command.assert_called_once_with(
            "ip addr add 192.168.1.1/24 dev eth0", self.host, sudo=True
        )

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_add_ipaddr_exception(self, mock_run_command):
        mock_run_command.side_effect = Exception("Boom!")
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.add_ipaddr("192.168.1.1", "255.255.255.0")

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_remove_ipaddr(self, mock_run_command):
        self.interface.remove_ipaddr("192.168.1.1", "255.255.255.0")
        mock_run_command.assert_called_once_with(
            "ip addr del 192.168.1.1/24 dev eth0", self.host, sudo=True
        )

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_remove_ipaddr_exception(self, mock_run_command):
        mock_run_command.side_effect = Exception("Boom!")
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.remove_ipaddr("192.168.1.1", "255.255.255.0")

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_flush_ipaddr(self, mock_run_command):
        self.interface.flush_ipaddr()
        mock_run_command.assert_called_once_with(
            "ip addr flush dev eth0", self.host, sudo=True
        )

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_flush_ipaddr_exception(self, mock_run_command):
        mock_run_command.side_effect = Exception("Boom!")
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.flush_ipaddr()

    def test_is_admin_link_up_exception(self):
        with unittest.mock.patch.object(
            self.interface,
            "_get_interface_details",
            side_effect=nw_exceptions.NWException,
        ):
            with self.assertRaises(nw_exceptions.NWException):
                self.interface.is_admin_link_up()

    def test_is_operational_link_up_exception(self):
        with unittest.mock.patch.object(
            self.interface,
            "_get_interface_details",
            side_effect=nw_exceptions.NWException,
        ):
            with self.assertRaises(nw_exceptions.NWException):
                self.interface.is_operational_link_up()

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_is_available(self, mock_run_command):
        self.assertTrue(self.interface.is_available())
        mock_run_command.side_effect = Exception("Boom!")
        self.assertFalse(self.interface.is_available())

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_is_bond(self, mock_run_command):
        self.assertTrue(self.interface.is_bond())
        mock_run_command.side_effect = Exception("Boom!")
        self.assertFalse(self.interface.is_bond())

    def test_is_admin_link_up(self):
        with unittest.mock.patch.object(
            self.interface, "_get_interface_details"
        ) as mock_get_details:
            mock_get_details.return_value = {"flags": ["UP"]}
            self.assertTrue(self.interface.is_admin_link_up())
            mock_get_details.return_value = {"flags": ["DOWN"]}
            self.assertFalse(self.interface.is_admin_link_up())

    def test_is_operational_link_up(self):
        with unittest.mock.patch.object(
            self.interface, "_get_interface_details"
        ) as mock_get_details:
            mock_get_details.return_value = {"flags": ["LOWER_UP"]}
            self.assertTrue(self.interface.is_operational_link_up())
            mock_get_details.return_value = {"flags": ["DOWN"]}
            self.assertFalse(self.interface.is_operational_link_up())

    def test_is_link_up(self):
        with unittest.mock.patch.object(
            self.interface, "is_admin_link_up", return_value=True
        ):
            with unittest.mock.patch.object(
                self.interface, "is_operational_link_up", return_value=True
            ):
                self.assertTrue(self.interface.is_link_up())
            with unittest.mock.patch.object(
                self.interface, "is_operational_link_up", return_value=False
            ):
                self.assertFalse(self.interface.is_link_up())

    @unittest.mock.patch("builtins.open", new_callable=unittest.mock.mock_open)
    def test_vlans(self, mock_open):
        with unittest.mock.patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            mock_open.return_value.__enter__.return_value = iter(["vlan1 | 1 | eth0"])
            self.assertEqual(self.interface.vlans, {"1": "vlan1"})

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_add_vlan_tag(self, mock_run_command):
        self.interface.add_vlan_tag(100)
        mock_run_command.assert_called_with(
            "ip link add link eth0 name eth0.100 type vlan id 100",
            self.host,
            sudo=True,
        )

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_add_vlan_tag_exception(self, mock_run_command):
        mock_run_command.side_effect = Exception("Boom!")
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.add_vlan_tag(100)

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_remove_vlan_by_tag(self, mock_run_command):
        with unittest.mock.patch.object(
            interfaces.NetworkInterface,
            "vlans",
            new_callable=unittest.mock.PropertyMock,
        ) as mock_vlans:
            mock_vlans.return_value = {"100": "eth0.100"}
            self.assertTrue(self.interface.remove_vlan_by_tag(100))
            mock_run_command.assert_called_with(
                "ip link delete eth0.100", self.host, sudo=True
            )
            self.assertFalse(self.interface.remove_vlan_by_tag(101))

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_remove_vlan_by_tag_exception(self, mock_run_command):
        mock_run_command.side_effect = Exception("Boom!")
        with unittest.mock.patch.object(
            interfaces.NetworkInterface,
            "vlans",
            new_callable=unittest.mock.PropertyMock,
        ) as mock_vlans:
            mock_vlans.return_value = {"100": "eth0.100"}
            with self.assertRaises(nw_exceptions.NWException):
                self.interface.remove_vlan_by_tag(100)

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_remove_all_vlans(self, mock_run_command):
        with unittest.mock.patch.object(
            interfaces.NetworkInterface,
            "vlans",
            new_callable=unittest.mock.PropertyMock,
        ) as mock_vlans:
            mock_vlans.return_value = {"100": "eth0.100", "200": "eth0.200"}
            self.interface.remove_all_vlans()
            self.assertEqual(mock_run_command.call_count, 2)

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_remove_all_vlans_exception(self, mock_run_command):
        mock_run_command.side_effect = Exception("Boom!")
        with unittest.mock.patch.object(
            interfaces.NetworkInterface,
            "vlans",
            new_callable=unittest.mock.PropertyMock,
        ) as mock_vlans:
            mock_vlans.return_value = {"100": "eth0.100"}
            with self.assertRaises(nw_exceptions.NWException):
                self.interface.remove_all_vlans()

    @unittest.mock.patch("avocado.utils.network.interfaces.distro_detect")
    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_save_rhel9(self, mock_run_command, mock_distro_detect):
        distro_mock = unittest.mock.MagicMock()
        distro_mock.name = "rhel"
        distro_mock.version = "9"
        mock_distro_detect.return_value = distro_mock
        with unittest.mock.patch.object(
            self.interface, "get_ipaddrs", return_value=["192.168.1.1"]
        ), unittest.mock.patch(
            "os.path.exists", return_value=False
        ), unittest.mock.patch(
            "shutil.copy"
        ), unittest.mock.patch.object(
            self.interface, "_move_file_to_backup"
        ):
            self.interface.save("192.168.1.1", "255.255.255.0")
        self.assertTrue(self.interface.distro_is_rhel9_or_later)
        self.assertEqual(mock_run_command.call_count, 3)

    @unittest.mock.patch("avocado.utils.network.interfaces.distro_detect")
    @unittest.mock.patch(
        "avocado.utils.network.interfaces.NetworkInterface._write_to_file"
    )
    def test_save_rhel8_or_older(self, mock_write_to_file, mock_distro_detect):
        distro_mock = unittest.mock.MagicMock()
        distro_mock.name = "rhel"
        distro_mock.version = "8"
        mock_distro_detect.return_value = distro_mock
        with unittest.mock.patch.object(
            self.interface, "get_ipaddrs", return_value=["192.168.1.1"]
        ):
            self.interface.save("192.168.1.1", "255.255.255.0")
            expected_dict = {
                "TYPE": "Ethernet",
                "BOOTPROTO": "static",
                "NAME": "eth0",
                "DEVICE": "eth0",
                "ONBOOT": "yes",
                "IPADDR": "192.168.1.1",
                "NETMASK": "255.255.255.0",
                "IPV6INIT": "yes",
                "IPV6_AUTOCONF": "yes",
                "IPV6_DEFROUTE": "yes",
            }
            mock_write_to_file.assert_called_once_with(
                "/etc/sysconfig/network-scripts/ifcfg-eth0", expected_dict
            )

    @unittest.mock.patch("avocado.utils.network.interfaces.distro_detect")
    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_save_rhel9_bond(self, mock_run_command, mock_distro_detect):
        distro_mock = unittest.mock.MagicMock()
        distro_mock.name = "rhel"
        distro_mock.version = "9"
        mock_distro_detect.return_value = distro_mock
        self.interface.if_type = "Bond"
        with unittest.mock.patch.object(
            self.interface, "get_ipaddrs", return_value=["192.168.1.1"]
        ), unittest.mock.patch.object(
            self.interface,
            "_get_bondinterface_details",
            return_value={"mode": ["active-backup"], "slaves": ["eth1"]},
        ), unittest.mock.patch(
            "os.path.exists", return_value=False
        ), unittest.mock.patch(
            "shutil.copy"
        ), unittest.mock.patch.object(
            self.interface, "_move_file_to_backup"
        ):
            self.interface.save("192.168.1.1", "255.255.255.0")
            self.assertEqual(mock_run_command.call_count, 3)

    @unittest.mock.patch("avocado.utils.network.interfaces.distro_detect")
    def test_save_suse(self, mock_distro_detect):
        distro_mock = unittest.mock.MagicMock()
        distro_mock.name = "SuSE"
        distro_mock.version = "15"
        mock_distro_detect.return_value = distro_mock
        with unittest.mock.patch.object(
            self.interface, "get_ipaddrs", return_value=["192.168.1.1"]
        ), unittest.mock.patch.object(self.interface, "_write_to_file") as mock_write:
            self.interface.save("192.168.1.1", "255.255.255.0")
            mock_write.assert_called()

    @unittest.mock.patch("avocado.utils.network.interfaces.distro_detect")
    def test_save_suse_bond(self, mock_distro_detect):
        distro_mock = unittest.mock.MagicMock()
        distro_mock.name = "SuSE"
        distro_mock.version = "15"
        mock_distro_detect.return_value = distro_mock
        self.interface.if_type = "Bond"
        with unittest.mock.patch.object(
            self.interface, "get_ipaddrs", return_value=["192.168.1.1"]
        ), unittest.mock.patch.object(
            self.interface,
            "_get_bondinterface_details",
            return_value={"mode": ["active-backup"], "slaves": ["eth1"]},
        ), unittest.mock.patch.object(
            self.interface, "_write_to_file"
        ) as mock_write:
            self.interface.save("192.168.1.1", "255.255.255.0")
            self.assertEqual(mock_write.call_count, 2)

    @unittest.mock.patch("avocado.utils.network.interfaces.distro_detect")
    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_save_suse16_bond(self, mock_run_command, mock_distro_detect):
        distro_mock = unittest.mock.MagicMock()
        distro_mock.name = "SuSE"
        distro_mock.version = "16"
        mock_distro_detect.return_value = distro_mock
        self.interface.if_type = "Bond"
        with unittest.mock.patch.object(
            self.interface, "get_ipaddrs", return_value=["192.168.1.1"]
        ), unittest.mock.patch.object(
            self.interface,
            "_get_bondinterface_details",
            return_value={"mode": ["active-backup"], "slaves": ["eth1"]},
        ), unittest.mock.patch(
            "os.path.exists", return_value=False
        ), unittest.mock.patch(
            "shutil.copy"
        ), unittest.mock.patch.object(
            self.interface, "_move_file_to_backup"
        ):
            self.interface.save("192.168.1.1", "255.255.255.0")
            self.assertEqual(mock_run_command.call_count, 3)

    @unittest.mock.patch("avocado.utils.network.interfaces.distro_detect")
    def test_save_unsupported_distro(self, mock_distro_detect):
        distro_mock = unittest.mock.MagicMock()
        distro_mock.name = "unknown"
        mock_distro_detect.return_value = distro_mock
        with unittest.mock.patch.object(
            self.interface, "get_ipaddrs", return_value=["192.168.1.1"]
        ):
            with self.assertRaises(nw_exceptions.NWException):
                self.interface.save("192.168.1.1", "255.255.255.0")

    def test_save_no_ip(self):
        with unittest.mock.patch.object(self.interface, "get_ipaddrs", return_value=[]):
            with self.assertRaises(nw_exceptions.NWException):
                self.interface.save("192.168.1.1", "255.255.255.0")

    @unittest.mock.patch("avocado.utils.network.interfaces.distro_detect")
    @unittest.mock.patch(
        "avocado.utils.network.interfaces.NetworkInterface._write_to_file"
    )
    def test_save_rhel8_or_older_bond(self, mock_write_to_file, mock_distro_detect):
        distro_mock = unittest.mock.MagicMock()
        distro_mock.name = "rhel"
        distro_mock.version = "8"
        mock_distro_detect.return_value = distro_mock
        self.interface.if_type = "Bond"
        with unittest.mock.patch.object(
            self.interface, "get_ipaddrs", return_value=["192.168.1.1"]
        ), unittest.mock.patch.object(
            self.interface,
            "_get_bondinterface_details",
            return_value={"mode": ["active-backup"], "slaves": ["eth1"]},
        ):
            self.interface.save("192.168.1.1", "255.255.255.0")
            self.assertEqual(mock_write_to_file.call_count, 2)

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_are_packets_lost_true(self, mock_run_command):
        mock_run_command.return_value = "100% packet loss"
        self.assertTrue(self.interface.are_packets_lost("192.168.1.2"))

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_are_packets_lost_no_loss(self, mock_run_command):
        mock_run_command.return_value = "0% packet loss"
        self.assertFalse(self.interface.are_packets_lost("192.168.1.2"))

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_are_packets_lost_false(self, mock_run_command):
        mock_run_command.return_value = "invalid output"
        self.assertTrue(self.interface.are_packets_lost("192.168.1.2"))

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_are_packets_lost_exception(self, mock_run_command):
        mock_run_command.side_effect = Exception("Boom!")
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.are_packets_lost("192.168.1.2")

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_get_bondinterface_details(self, mock_run_command):
        mock_run_command.return_value = "mode\nslave1 slave2"
        details = self.interface._get_bondinterface_details()
        self.assertEqual(details, {"mode": ["mode"], "slaves": ["slave1", "slave2"]})
        mock_run_command.side_effect = Exception("Boom!")
        with self.assertRaises(nw_exceptions.NWException):
            self.interface._get_bondinterface_details()

    @unittest.mock.patch("shutil.move")
    @unittest.mock.patch("os.path.exists")
    def test_move_file_to_backup_exception(self, mock_exists, mock_move):
        mock_exists.return_value = False
        with self.assertRaises(nw_exceptions.NWException):
            self.interface._move_file_to_backup(
                "nonexistent_file", ignore_missing=False
            )
        mock_move.assert_not_called()

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_remove_link(self, mock_run_command):
        self.interface.remove_link()
        mock_run_command.assert_called_once_with(
            "ip link del dev eth0", self.host, sudo=True
        )
        mock_run_command.side_effect = Exception("Boom!")
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.remove_link()

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_nm_flush_ipaddr(self, mock_run_command):
        mock_run_command.return_value = "192.168.1.1/24"
        self.interface.nm_flush_ipaddr()
        self.assertEqual(mock_run_command.call_count, 2)
        mock_run_command.return_value = ""
        self.interface.nm_flush_ipaddr()
        self.assertEqual(mock_run_command.call_count, 3)

    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_nm_flush_ipaddr_exception(self, mock_run_command):
        mock_run_command.side_effect = [
            "192.168.1.1/24",
            Exception("Boom!"),
        ]
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.nm_flush_ipaddr()

    @unittest.mock.patch("shutil.move")
    @unittest.mock.patch("os.path.exists")
    def test_restore_from_backup(self, mock_exists, mock_move):
        with unittest.mock.patch.object(
            interfaces.NetworkInterface,
            "config_filename",
            new_callable=unittest.mock.PropertyMock,
        ) as mock_config_filename:
            mock_config_filename.return_value = "/tmp/ifcfg-eth0"
            mock_exists.return_value = True
            self.interface.restore_from_backup()
            mock_move.assert_called_once_with(
                "/tmp/ifcfg-eth0.backup", "/tmp/ifcfg-eth0"
            )
            mock_exists.return_value = False
            with self.assertRaises(nw_exceptions.NWException):
                self.interface.restore_from_backup()

    @unittest.mock.patch("shutil.move")
    @unittest.mock.patch("os.path.exists")
    def test_restore_slave_cfg_file(self, mock_exists, mock_move):
        self.interface.if_type = "Bond"
        mock_exists.return_value = True
        with unittest.mock.patch.object(
            interfaces.NetworkInterface,
            "slave_config_filename",
            new_callable=unittest.mock.PropertyMock,
        ) as mock_slave_config_filename:
            mock_slave_config_filename.return_value = ["/tmp/ifcfg-eth1"]
            self.interface.restore_slave_cfg_file()
            mock_move.assert_called_once_with(
                "/tmp/ifcfg-eth1.backup", "/tmp/ifcfg-eth1"
            )

    def test_restore_slave_cfg_file_not_bond(self):
        self.interface.if_type = "Ethernet"
        with unittest.mock.patch("shutil.move") as mock_move:
            self.interface.restore_slave_cfg_file()
            mock_move.assert_not_called()

    @unittest.mock.patch("os.remove")
    @unittest.mock.patch("os.path.exists")
    def test_restore_slave_cfg_file_no_backup(self, mock_exists, mock_remove):
        self.interface.if_type = "Bond"
        mock_exists.return_value = False
        with unittest.mock.patch.object(
            interfaces.NetworkInterface,
            "slave_config_filename",
            new_callable=unittest.mock.PropertyMock,
        ) as mock_slave_config_filename:
            mock_slave_config_filename.return_value = ["/tmp/ifcfg-eth1"]
            self.interface.restore_slave_cfg_file()
            mock_remove.assert_called_once_with("/tmp/ifcfg-eth1")

    @unittest.mock.patch("os.path.isfile")
    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_is_veth(self, mock_run_command, mock_isfile):
        mock_isfile.return_value = True
        mock_run_command.return_value = "l-lan"
        self.assertTrue(self.interface.is_veth())
        mock_run_command.return_value = "other"
        self.assertFalse(self.interface.is_veth())
        mock_isfile.return_value = False
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.is_veth()

    @unittest.mock.patch("os.path.isfile")
    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_is_vnic(self, mock_run_command, mock_isfile):
        mock_isfile.return_value = True
        mock_run_command.return_value = "vnic"
        self.assertTrue(self.interface.is_vnic())
        mock_run_command.return_value = "other"
        self.assertFalse(self.interface.is_vnic())
        mock_isfile.return_value = False
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.is_vnic()

    @unittest.mock.patch("os.path.isfile")
    @unittest.mock.patch("avocado.utils.network.interfaces.run_command")
    def test_is_sriov(self, mock_run_command, mock_isfile):
        mock_isfile.return_value = True
        mock_run_command.return_value = "VF_something_SN"
        self.assertTrue(self.interface.is_sriov())
        mock_run_command.return_value = "other"
        self.assertFalse(self.interface.is_sriov())
        mock_isfile.return_value = False
        with self.assertRaises(nw_exceptions.NWException):
            self.interface.is_sriov()

    @unittest.mock.patch("os.remove")
    @unittest.mock.patch("os.path.isfile")
    def test_remove_cfg_file(self, mock_isfile, mock_remove):
        with unittest.mock.patch.object(
            interfaces.NetworkInterface,
            "config_filename",
            new_callable=unittest.mock.PropertyMock,
        ) as mock_config_filename:
            mock_config_filename.return_value = "/tmp/ifcfg-eth0"
            mock_isfile.return_value = True
            self.interface.remove_cfg_file()
            mock_remove.assert_called_once_with("/tmp/ifcfg-eth0")
            mock_isfile.return_value = False
            self.interface.remove_cfg_file()
            # assert that os.remove was not called again
            mock_remove.assert_called_once()

    @unittest.mock.patch("subprocess.Popen")
    def test_ping_flood(self, mock_popen):
        mock_process = unittest.mock.MagicMock()
        mock_process.stdout.read.return_value = "........"
        mock_popen.return_value.__enter__.return_value = mock_process
        self.assertTrue(
            interfaces.NetworkInterface.ping_flood("eth0", "192.168.1.2", 10)
        )
        mock_process.stdout.read.return_value = "." * 10
        self.assertFalse(
            interfaces.NetworkInterface.ping_flood("eth0", "192.168.1.2", 10)
        )

    @unittest.mock.patch("subprocess.Popen")
    def test_ping_flood_success(self, mock_popen):
        mock_process = unittest.mock.MagicMock()
        mock_process.stdout.read.return_value = "......"
        mock_popen.return_value.__enter__.return_value = mock_process
        self.assertTrue(
            interfaces.NetworkInterface.ping_flood("eth0", "192.168.1.2", 10)
        )

    def test_get_device_IPI_name_vnic(self):
        with unittest.mock.patch.object(
            self.interface, "is_vnic", return_value=True
        ), unittest.mock.patch(
            "avocado.utils.process.system_output"
        ) as mock_system_output:
            mock_system_output.side_effect = [
                b"vnic@30000009",
                b"vnic-30000009",
            ]
            self.assertEqual(self.interface.get_device_IPI_name(), "vnic-30000009")

    def test_get_device_IPI_name_veth(self):
        with unittest.mock.patch.object(
            self.interface, "is_vnic", return_value=False
        ), unittest.mock.patch.object(self.interface, "is_veth", return_value=True):
            self.assertEqual(self.interface.get_device_IPI_name(), "eth0")

    def test_get_device_IPI_name_unsupported(self):
        with unittest.mock.patch.object(
            self.interface, "is_vnic", return_value=False
        ), unittest.mock.patch.object(self.interface, "is_veth", return_value=False):
            self.assertIsNone(self.interface.get_device_IPI_name())


if __name__ == "__main__":
    unittest.main()
