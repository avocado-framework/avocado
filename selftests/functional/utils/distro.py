import os
import platform

from avocado import Test
from avocado.core.exit_codes import AVOCADO_ALL_OK
from avocado.core.job import Job
from avocado.core.nrunner.runnable import Runnable
from avocado.core.suite import TestSuite
from avocado.utils import distro


class Distro(Test):
    """Tests distro detection in containers

    :avocado: dependency={"type": "package", "name": "podman", "action": "check"}
    """

    def run_job(self, podman_image, output):
        """Runs an Avocado job on a container, returning the stdout of the one
        and only runnable executed (equivalent to an "avocado distro" command).
        """
        config = {
            "run.spawner": "podman",
            "spawner.podman.image": podman_image,
            "run.results_dir": self.workdir,
        }
        runnable = Runnable("exec-test", "python3", "-m", "avocado", "distro")
        suite = TestSuite("1", config, tests=[runnable])
        with Job(config, test_suites=[suite]) as job:
            result = job.run()
            self.assertEqual(result, AVOCADO_ALL_OK, "Job execution failed")

        stdout_path = os.path.join(job.test_results_path, "1-1-python3", "stdout")
        with open(stdout_path, "rb") as stdout:
            self.assertEqual(stdout.read(), output)

    def test_fedora_38(self):
        """
        :avocado: dependency={"type": "podman-image", "uri": "registry.fedoraproject.org/fedora:38"}
        """
        self.run_job(
            "registry.fedoraproject.org/fedora:38",
            b"Detected distribution: fedora ("
            + os.uname().machine.encode()
            + b") version 38 release 0\n",
        )

    def test_rhel_9_1(self):
        """
        :avocado: dependency={"type": "podman-image", "uri": "registry.access.redhat.com/ubi9:9.1"}
        """
        self.run_job(
            "registry.access.redhat.com/ubi9:9.1",
            b"Detected distribution: rhel ("
            + os.uname().machine.encode()
            + b") version 9 release 1\n",
        )

    def test_debian_12_7(self):
        """
        :avocado: dependency={"type": "podman-image", "uri": "docker.io/library/python@sha256:785fef11f44b7393c03d77032fd72e56af8b05442b051a151229145e5fbbcb29"}
        """
        self.run_job(
            "docker.io/library/python@sha256:785fef11f44b7393c03d77032fd72e56af8b05442b051a151229145e5fbbcb29",
            b"Detected distribution: debian ("
            + os.uname().machine.encode()
            + b") version 12 release 7\n",
        )


class DistroDetectLocal(Test):
    """Tests distro detection on the local system without containers."""

    def test_detect_current_system(self):
        """Verify detect() returns a valid result for the running system."""
        result = distro.detect()
        self.assertIsInstance(result, distro.LinuxDistro)
        has_release_file = any(
            os.path.exists(p)
            for p in [
                "/etc/os-release",
                "/etc/redhat-release",
                "/etc/fedora-release",
                "/etc/debian_version",
            ]
        )
        if has_release_file:
            self.assertNotEqual(
                result.name,
                distro.UNKNOWN_DISTRO_NAME,
                "detect() should identify a known distro on this system",
            )
            self.assertEqual(result.arch, platform.machine())
