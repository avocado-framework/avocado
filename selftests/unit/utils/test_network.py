import socket
import unittest.mock

import avocado.utils.network.ports as ports

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

    @unittest.skipUnless(HAS_NETIFACES,
                         "netifaces library not available")
    def test_is_port_free(self):
        port = ports.find_free_port(sequent=False)
        self.assertTrue(ports.is_port_free(port, "localhost"))
        ipv4_addrs, ipv6_addrs = get_all_local_addrs()
        good = []
        bad = []
        skip = []
        sock = None
        for family in ports.FAMILIES:
            if family == socket.AF_INET:
                addrs = ipv4_addrs
            else:
                addrs = ipv6_addrs
            for addr in addrs:
                for protocol in ports.PROTOCOLS:
                    try:
                        sock = socket.socket(family, protocol)
                        sock.bind((addr, port))
                        if ports.is_port_free(port, "localhost"):
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
