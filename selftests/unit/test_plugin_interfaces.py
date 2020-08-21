import unittest

from avocado.core import plugin_interfaces


class Plugin(unittest.TestCase):

    def test_instantiate_settings(self):
        with self.assertRaises(TypeError):
            # pylint: disable=E0110
            plugin_interfaces.Settings()

    def test_instantiate_cli(self):
        with self.assertRaises(TypeError):
            # pylint: disable=E0110
            plugin_interfaces.CLI()

    def test_instantiate_cli_cmd(self):
        with self.assertRaises(TypeError):
            # pylint: disable=E0110
            plugin_interfaces.CLICmd()

    def test_instantiate_job_pre(self):
        with self.assertRaises(TypeError):
            # pylint: disable=E0110
            plugin_interfaces.JobPre()

    def test_instantiate_job_post(self):
        with self.assertRaises(TypeError):
            # pylint: disable=E0110
            plugin_interfaces.JobPost()

    def test_instantiate_result(self):
        with self.assertRaises(TypeError):
            # pylint: disable=E0110
            plugin_interfaces.Result()

    def test_instantiate_job_pre_tests(self):
        with self.assertRaises(TypeError):
            # pylint: disable=E0110
            plugin_interfaces.JobPreTests()

    def test_instantiate_job_post_tests(self):
        with self.assertRaises(TypeError):
            # pylint: disable=E0110
            plugin_interfaces.JobPostTests()

    def test_instantiate_result_events(self):
        with self.assertRaises(TypeError):
            # pylint: disable=E0110
            plugin_interfaces.ResultEvents()

    def test_instantiate_varianter(self):
        with self.assertRaises(TypeError):
            # pylint: disable=E0110
            plugin_interfaces.Varianter()

    def test_instantiate_init(self):
        with self.assertRaises(TypeError):
            # pylint: disable=E0110
            plugin_interfaces.Init()

    def test_instantiate_spawner(self):
        with self.assertRaises(TypeError):
            # pylint: disable=E0110
            plugin_interfaces.Spawner()
