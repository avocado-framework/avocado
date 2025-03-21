import unittest

from avocado import Test
from avocado.utils import vmimage
from selftests.utils import missing_binary


@unittest.skipIf(
    missing_binary("qemu-img"),
    "QEMU disk image utility is required by the vmimage utility ",
)
class VmimageTest(Test):
    """
    Example demonstrating VM image dependency.
    The vmimage dependency runner will ensure the required VM image
    is downloaded and cached before the test execution begins.

    This example uses Fedora, but the same approach works for other providers
    such as CentOS, Debian, Ubuntu, etc. Just change the provider, version,
    and architecture parameters as needed.

    :avocado: dependency={"type": "vmimage", "provider": "fedora", "version": "41", "arch": "x86_64"}
    """

    def test_vmimage(self):
        """
        Simple example showing how to use vmimage.get to verify the image exists.
        """
        # Get the VM image based on the dependency parameters
        image = vmimage.get(name="fedora", version="41", arch="x86_64")

        # Log the image path
        self.log.info("VM image path: %s", image.path)

        # Verify the image exists
        self.assertTrue(image.path, "VM image not found")
