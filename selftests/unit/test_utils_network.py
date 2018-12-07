import netifaces
import socket
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from avocado.utils import network


class PortTrackerTest(unittest.TestCase):

    def test_register_port(self):
        tracker = network.PortTracker()
        network.is_port_free = mock.MagicMock(return_value=True)
        self.assertNotIn(22, tracker.retained_ports)
        tracker.register_port(22)
        network.is_port_free.assert_called_once_with(22, tracker.address)
        self.assertIn(22, tracker.retained_ports)

    def test_release_port_does_not_poke_system(self):
        tracker = network.PortTracker()
        tracker.release_port = mock.MagicMock()
        network.is_port_free = mock.MagicMock()
        tracker.release_port(22)
        tracker.release_port.assert_called_once_with(22)
        network.is_port_free.assert_not_called()

    def test_release_port(self):
        tracker = network.PortTracker()
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
    return ipv4_addrs, ipv6_addrs


class FreePort(unittest.TestCase):

    def test_is_port_free(self):
        port = network.find_free_port(sequent=False)
        self.assertTrue(network.is_port_free(port, "localhost"))
        local_addrs = get_all_local_addrs()
        ipv4_addrs = ["localhost", ""] + list(local_addrs[0])
        ipv6_addrs = ["localhost", ""] + list(local_addrs[1])
        good = []
        bad = []
        skip = []
        sock = None
        for family in network.FAMILIES:
            if family == socket.AF_INET:
                addrs = ipv4_addrs
            else:
                addrs = ipv6_addrs
            for addr in addrs:
                for protocol in network.PROTOCOLS:
                    try:
                        sock = socket.socket(family, protocol)
                        sock.bind((addr, port))
                        if network.is_port_free(port, "localhost"):
                            bad.append("%s, %s, %s: reports free"
                                       % (family, protocol, addr))
                        else:
                            good.append("%s, %s, %s" % (family, protocol,
                                                        addr))
                    except Exception as exc:
                        if getattr(exc, 'errno', None) in (-2, 2, 22, 94):
                            skip.append("%s, %s, %s: Not supported: %s"
                                        % (family, protocol, addr, exc))
                        else:
                            bad.append("%s, %s, %s: Failed to bind: %s"
                                       % (family, protocol, addr, exc))
                    finally:
                        if sock is not None:
                            sock.close()
        self.assertFalse(bad, "Following combinations failed:\n%s\n\n"
                         "Following combinations passed:\n%s\n\n"
                         "Following combinations were skipped:\n%s"
                         % ("\n".join(bad), "\n".join(good), "\n".join(skip)))


if __name__ == "__main__":
    unittest.main()
