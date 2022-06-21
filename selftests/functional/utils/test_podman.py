from avocado import Test
from avocado.utils.podman import Podman


class PodmanTest(Test):

    async def test_python_version(self):
        """
        :avocado: dependency={"type": "package", "name": "podman", "action": "check"}
        :avocado: tags=slow
        """
        podman = Podman()
        result = await podman.get_python_version('fedora:34')
        self.assertEqual(result, (3, 9, '/usr/bin/python3'))
