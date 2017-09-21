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


if __name__ == "__main__":
    unittest.main()
