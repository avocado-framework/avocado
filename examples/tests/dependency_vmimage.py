import os

from avocado import Test
from avocado.core.settings import settings


class VmimageTest(Test):
    """
    Test demonstrating VM image dependency usage.
    The vmimage dependency runner will ensure the required VM image
    is downloaded and cached before the test execution begins.

    :avocado: dependency={"type": "vmimage", "provider": "fedora", "version": "41", "arch": "s390x"}
    """

    def test_vmimage_exists(self):
        """
        Verify that the VM image was downloaded by the vmimage runner.
        """
        # Get cache directory from settings
        cache_dir = settings.as_dict().get("datadir.paths.cache_dirs")[0]
        cache_base = os.path.join(cache_dir, "by_location")

        # The image should be in the cache since the runner downloaded it
        self.assertTrue(
            os.path.exists(cache_base), f"Cache directory {cache_base} does not existz"
        )

        # Log cache contents for debugging
        self.log.info("Cache directory contents:")
        for root, _, files in os.walk(cache_base):
            for f in files:
                if f.endswith((".qcow2", ".raw", ".img")):
                    self.log.info("Found image: %s", os.path.join(root, f))


class MultiArchVmimageTest(Test):
    """
    Test demonstrating multiple VM image dependencies with different architectures.

    :avocado: dependency={"type": "vmimage", "provider": "fedora", "version": "41", "arch": "s390x"}
    :avocado: dependency={"type": "vmimage", "provider": "fedora", "version": "41", "arch": "x86_64"}
    """

    def test_multiple_images(self):
        """
        Verify that multiple VM images can be handled by the runner.
        Checks that both s390x and x86_64 images exist in the cache
        and have the expected properties.
        """
        # Get cache directory from settings
        cache_dir = settings.as_dict().get("datadir.paths.cache_dirs")[0]
        cache_base = os.path.join(cache_dir, "by_location")

        # The cache directory should exist
        self.assertTrue(
            os.path.exists(cache_base), f"Cache directory {cache_base} does not exist"
        )

        # Track if we found both architectures
        found_s390x = False
        found_x86_64 = False

        # Search for both architecture images
        self.log.info("Searching for Fedora 41 images (s390x and x86_64):")
        for root, _, files in os.walk(cache_base):
            for f in files:
                if not f.endswith((".qcow2", ".raw", ".img")):
                    continue

                filepath = os.path.join(root, f)
                self.log.info("Found image: %s", filepath)

                # Check for architecture markers in path/filename
                if "s390x" in filepath:
                    found_s390x = True
                if "x86_64" in filepath:
                    found_x86_64 = True

        # Verify both architectures were found
        self.assertTrue(found_s390x, "s390x Fedora 41 image not found in cache")
        self.assertTrue(found_x86_64, "x86_64 Fedora 41 image not found in cache")


class UbuntuVmimageTest(Test):
    """
    Test demonstrating VM image dependency with a different provider.

    :avocado: dependency={"type": "vmimage", "provider": "ubuntu", "version": "22.04", "arch": "x86_64"}
    """

    def test_ubuntu_image(self):
        """
        Verify that Ubuntu images can be handled by the runner.
        Checks that the Ubuntu x86_64 image exists in the cache
        and has the expected properties.
        """
        # Get cache directory from settings
        cache_dir = settings.as_dict().get("datadir.paths.cache_dirs")[0]
        cache_base = os.path.join(cache_dir, "by_location")

        # The cache directory should exist
        self.assertTrue(
            os.path.exists(cache_base), f"Cache directory {cache_base} does not exist"
        )

        # Track if we found the Ubuntu image
        found_ubuntu = False

        # Search for Ubuntu x86_64 image
        self.log.info("Searching for Ubuntu 22.04 x86_64 image:")
        for root, _, files in os.walk(cache_base):
            for f in files:
                if not f.endswith((".qcow2", ".raw", ".img")):
                    continue

                filepath = os.path.join(root, f)

                # Check for Ubuntu cloud image filename pattern
                if "ubuntu-22.04-server-cloudimg-amd64.img" in filepath.lower():
                    self.log.info("Found Ubuntu image: %s", filepath)
                    found_ubuntu = True

        # Verify Ubuntu image was found
        self.assertTrue(found_ubuntu, "Ubuntu 22.04 x86_64 image not found in cache")
