import os

from avocado import Test
from avocado.core.settings import settings


class FedoraS390xVmimageTest(Test):
    """
    Test demonstrating VM image dependency with Fedora s390x architecture.
    The vmimage dependency runner will ensure the required VM image
    is downloaded and cached before the test execution begins.

    :avocado: dependency={"type": "vmimage", "provider": "fedora", "version": "41", "arch": "s390x"}
    """

    def test_fedora_s390x_image(self):
        """
        Verify that the Fedora s390x image was downloaded by the vmimage runner.
        """
        # Get cache directory from settings
        cache_dir = settings.as_dict().get("datadir.paths.cache_dirs")[0]
        cache_base = os.path.join(cache_dir, "by_location")

        # The image should be in the cache since the runner downloaded it
        self.assertTrue(
            os.path.exists(cache_base), f"Cache directory {cache_base} does not exist"
        )

        # Track if we found the Fedora s390x image
        found_fedora_s390x = False

        # Search for Fedora s390x image
        self.log.info("Searching for Fedora 41 s390x image:")
        for root, _, files in os.walk(cache_base):
            for f in files:
                if not f.endswith((".qcow2", ".raw", ".img")):
                    continue

                filepath = os.path.join(root, f)

                # Check for Fedora s390x image
                if "fedora" in filepath.lower() and "s390x" in filepath.lower():
                    self.log.info("Found Fedora s390x image: %s", filepath)
                    found_fedora_s390x = True

        # Verify Fedora s390x image was found
        self.assertTrue(found_fedora_s390x, "Fedora 41 s390x image not found in cache")


class FedoraX86VmimageTest(Test):
    """
    Test demonstrating VM image dependency with Fedora x86_64 architecture.

    :avocado: dependency={"type": "vmimage", "provider": "fedora", "version": "41", "arch": "x86_64"}
    """

    def test_fedora_x86_image(self):
        """
        Verify that Fedora x86_64 images can be handled by the runner.
        Checks that the Fedora x86_64 image exists in the cache
        and has the expected properties.
        """
        # Get cache directory from settings
        cache_dir = settings.as_dict().get("datadir.paths.cache_dirs")[0]
        cache_base = os.path.join(cache_dir, "by_location")

        # The cache directory should exist
        self.assertTrue(
            os.path.exists(cache_base), f"Cache directory {cache_base} does not exist"
        )

        # Track if we found the Fedora x86_64 image
        found_fedora_x86 = False

        # Search for Fedora x86_64 image
        self.log.info("Searching for Fedora 41 x86_64 image:")
        for root, _, files in os.walk(cache_base):
            for f in files:
                if not f.endswith((".qcow2", ".raw", ".img")):
                    continue

                filepath = os.path.join(root, f)

                # Check for Fedora x86_64 image
                if "fedora" in filepath.lower() and "x86_64" in filepath.lower():
                    self.log.info("Found Fedora x86_64 image: %s", filepath)
                    found_fedora_x86 = True

        # Verify Fedora x86_64 image was found
        self.assertTrue(found_fedora_x86, "Fedora 41 x86_64 image not found in cache")


class CentOSVmimageTest(Test):
    """
    Test demonstrating VM image dependency with CentOS.

    :avocado: dependency={"type": "vmimage", "provider": "centos", "version": "8", "arch": "x86_64"}
    """

    def test_centos_image(self):
        """
        Verify that CentOS images can be handled by the runner.
        Checks that the CentOS x86_64 image exists in the cache
        and has the expected properties.
        """
        # Get cache directory from settings
        cache_dir = settings.as_dict().get("datadir.paths.cache_dirs")[0]
        cache_base = os.path.join(cache_dir, "by_location")

        # The cache directory should exist
        self.assertTrue(
            os.path.exists(cache_base), f"Cache directory {cache_base} does not exist"
        )

        # Track if we found the CentOS image
        found_centos = False

        # Search for CentOS x86_64 image
        self.log.info("Searching for CentOS 8 x86_64 image:")
        for root, _, files in os.walk(cache_base):
            for f in files:
                if not f.endswith((".qcow2", ".raw", ".img")):
                    continue

                filepath = os.path.join(root, f)

                # Check for CentOS image filename pattern
                if "centos-8" in filepath.lower() and "x86_64" in filepath.lower():
                    self.log.info("Found CentOS image: %s", filepath)
                    found_centos = True

        # Verify CentOS image was found
        self.assertTrue(found_centos, "CentOS 8 x86_64 image not found in cache")


class DebianVmimageTest(Test):
    """
    Test demonstrating VM image dependency with Debian.

    :avocado: dependency={"type": "vmimage", "provider": "debian", "version": "bullseye", "arch": "x86_64"}
    """

    def test_debian_image(self):
        """
        Verify that Debian images can be handled by the runner.
        Checks that the Debian x86_64 image exists in the cache
        and has the expected properties.
        """
        # Get cache directory from settings
        cache_dir = settings.as_dict().get("datadir.paths.cache_dirs")[0]
        cache_base = os.path.join(cache_dir, "by_location")

        # The cache directory should exist
        self.assertTrue(
            os.path.exists(cache_base), f"Cache directory {cache_base} does not exist"
        )

        # Track if we found the Debian image
        found_debian = False

        # Search for Debian x86_64 image
        self.log.info("Searching for Debian Bullseye (11) x86_64 image:")
        for root, _, files in os.walk(cache_base):
            for f in files:
                if not f.endswith((".qcow2", ".raw", ".img")):
                    continue

                filepath = os.path.join(root, f)

                # Check for Debian image filename pattern
                if "debian-11-generic-amd64" in filepath.lower():
                    self.log.info("Found Debian image: %s", filepath)
                    found_debian = True

        # Verify Debian image was found
        self.assertTrue(
            found_debian, "Debian Bullseye (11) x86_64 image not found in cache"
        )


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
