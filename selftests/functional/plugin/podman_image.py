from avocado import Test
from avocado.utils.podman import Podman


class PodmanImageTest(Test):
    async def test(self):
        """
        :avocado: dependency={"type": "package", "name": "podman", "action": "check"}
        :avocado: dependency={"type": "podman-image", "uri": "registry.fedoraproject.org/fedora:38"}
        """
        podman = Podman()
        _, stdout, _ = await podman.execute(
            "images",
            "--filter",
            "reference=registry.fedoraproject.org/fedora:38",
            "--format",
            "{{.Repository}}:{{.Tag}}",
        )
        self.assertIn(
            "registry.fedoraproject.org/fedora:38",
            stdout.decode().splitlines(),
            "Podman image does not seem to have been pulled",
        )
