from avocado import Test
from avocado.utils.network.hosts import LocalHost
from avocado.utils.network.interfaces import NetworkInterface


class Interface(Test):
    def setUp(self):
        self.interface = NetworkInterface("lo", LocalHost("lo"))

    def test_ping_flood(self):
        self.assertTrue(self.interface.ping_flood("lo", "127.0.0.1", "1"))

    def test_ping_flood_fail(self):
        self.assertFalse(self.interface.ping_flood("lo", "172.16.1.1", "100"))
