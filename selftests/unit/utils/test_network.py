import unittest.mock

from avocado.utils.network import ports

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

    def test_release_port_does_not_poke_system(self):
        tracker = ports.PortTracker()
        tracker.release_port = unittest.mock.MagicMock()
        ports.is_port_free = unittest.mock.MagicMock()
        tracker.release_port(22)
        tracker.release_port.assert_called_once_with(22)
        ports.is_port_free.assert_not_called()

    def test_release_port(self):
        tracker = ports.PortTracker()
        tracker.retained_ports = [22]
        tracker.release_port(22)
        self.assertNotIn(22, tracker.retained_ports)


def get_all_local_addrs():
    """
    Returns all ipv4/ipv6 addresses that are associated with this machine
    """
    ipv4_addrs = []
    ipv6_addrs = []
    for interface in netifaces.interfaces():
        ifaddresses = netifaces.ifaddresses(interface)
        ipv4_addrs += [_['addr']
                       for _ in ifaddresses.get(netifaces.AF_INET, [])]
        ipv6_addrs += [_['addr']
                       for _ in ifaddresses.get(netifaces.AF_INET6, [])]
    if ipv4_addrs:
        ipv4_addrs += ["localhost", ""]
    if ipv6_addrs:
        ipv6_addrs += ["localhost", ""]
    return ipv4_addrs, ipv6_addrs


class FreePort(unittest.TestCase):

    def test_is_port_available(self):
        port = ports.find_free_port(sequent=False)
        result = ports.is_port_available(port, 'localhost')
        self.assertTrue(result)

    def test_find_free_port(self):
        port = ports.find_free_port(sequent=False)
        self.assertEqual(type(port), int)

    def test_find_free_ports(self):
        port = ports.find_free_ports(1000, 2000, 10)
        self.assertEqual(type(port), list)


if __name__ == "__main__":
    unittest.main()
