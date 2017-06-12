import unittest

from avocado.utils import simulation


class TestBridge(unittest.TestCase):

    def setUp(self):
        self.br = simulation.NetworkBridge("abc")

    def tearDown(self):
        self.br.clean()

    def test_bridge(self):
        self.br.clean()
        self.assertNotIn("abc",
                         process.run("brctl show", ignore_status=True).stdout)

        self.br = simulation.NetworkBridge("abc")
        time.sleep(2)
        self.assertIn("abc",
                      process.run("brctl show abc", ignore_status=True).stdout)
        self.br.clean()
        time.sleep(2)
        self.assertNotIn("abc",
                         process.run("brctl show", ignore_status=True).stdout)

    def test_dummy_interfaces(self):
        sim = simulation.SimulationNetwork(bridge=self.br)
        sim.addiface("x")
        sim.addiface("y")
        self.assertIn("link", sim.getValuesForDevice("x"))
        self.assertIn("link", sim.getValuesForDevice("y"))
        sim.clean()
        self.assertNotIn("link", sim.getValuesForDevice("x"))
        self.assertNotIn("link", sim.getValuesForDevice("y"))

    def test_virtual_ethernet_interfaces(self):
        sim = simulation.SimulationNetworkVeth(bridge=self.br)
        sim.addiface("x")
        sim.addiface("y")
        self.assertIn("link", sim.getValuesForDevice("x"))
        self.assertIn("link", sim.getValuesForDevice("y"))
        sim.clean()
        self.assertNotIn("link", sim.getValuesForDevice("x"))
        self.assertNotIn("link", sim.getValuesForDevice("y"))

    def test_tap_interfaces(self):
        sim = simulation.SimulationNetworkTap(bridge=self.br)
        sim.addiface("x")
        sim.addiface("y")
        self.assertIn("link", sim.getValuesForDevice("x"))
        self.assertIn("link", sim.getValuesForDevice("y"))
        sim.clean()
        self.assertNotIn("link", sim.getValuesForDevice("x"))
        self.assertNotIn("link", sim.getValuesForDevice("y"))
