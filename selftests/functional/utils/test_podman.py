import asyncio

from avocado import Test
from avocado.utils.podman import Podman


class PodmanTest(Test):

    def test_python_version(self):
        """
        :avocado: dependency={"type": "package", "name": "podman", "action": "check"}
        :avocado: tags=slow
        """
        podman = Podman()
        loop = asyncio.get_event_loop()
        coro = podman.get_python_version('fedora:34')
        result = loop.run_until_complete(coro)
        self.assertEqual(result, (3, 9, '/usr/bin/python3'))
