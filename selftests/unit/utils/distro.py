import os
import re
import tempfile
import unittest
import unittest.mock

from avocado.utils import distro


class LinuxDistroTest(unittest.TestCase):
    def test_init(self):
        dist = distro.LinuxDistro("fedora", "38", "0", "x86_64")
        self.assertEqual(dist.name, "fedora")
        self.assertEqual(dist.version, "38")
        self.assertEqual(dist.release, "0")
        self.assertEqual(dist.arch, "x86_64")

    def test_repr(self):
        dist = distro.LinuxDistro("rhel", "9", "1", "x86_64")
        self.assertEqual(
            repr(dist),
            "<LinuxDistro: name=rhel, version=9, release=1, arch=x86_64>",
        )


class ProbeTest(unittest.TestCase):
    def test_check_name_for_file_fail(self):
        class MyProbe(distro.Probe):
            CHECK_FILE = "/etc/issue"

        my_probe = MyProbe()
        self.assertFalse(my_probe.check_name_for_file())

    def test_check_name_for_file_contains_fail(self):
        class MyProbe(distro.Probe):
            CHECK_FILE = "/etc/issue"
            CHECK_FILE_CONTAINS = "text"

        my_probe = MyProbe()
        self.assertFalse(my_probe.check_name_for_file_contains())

    def test_check_version_fail(self):
        class MyProbe(distro.Probe):
            CHECK_VERSION_REGEX = re.compile(r"distro version (\d+)")

        my_probe = MyProbe()
        self.assertFalse(my_probe.check_version())

    def test_name_for_file(self):
        distro_file = "/etc/superdistro-issue"
        distro_name = "superdistro"

        class MyProbe(distro.Probe):
            CHECK_FILE = distro_file
            CHECK_FILE_DISTRO_NAME = distro_name

        my_probe = MyProbe()
        with unittest.mock.patch(
            "avocado.utils.distro.os.path.exists", return_value=True
        ) as mocked:
            probed_distro_name = my_probe.name_for_file()
            mocked.assert_called_once_with(distro_file)
        self.assertEqual(distro_name, probed_distro_name)

    def test_name_for_file_contains_match(self):
        fd, tmpfile = tempfile.mkstemp(suffix="-release")
        with os.fdopen(fd, "w") as tmp:
            tmp.write("Welcome to MyDistro 5.0\n")
        self.addCleanup(os.unlink, tmpfile)

        class MyProbe(distro.Probe):
            CHECK_FILE = tmpfile
            CHECK_FILE_CONTAINS = "MyDistro"
            CHECK_FILE_DISTRO_NAME = "mydistro"

        self.assertEqual(MyProbe().name_for_file_contains(), "mydistro")

    def test_name_for_file_contains_no_match(self):
        fd, tmpfile = tempfile.mkstemp(suffix="-release")
        with os.fdopen(fd, "w") as tmp:
            tmp.write("Some other content\n")
        self.addCleanup(os.unlink, tmpfile)

        class MyProbe(distro.Probe):
            CHECK_FILE = tmpfile
            CHECK_FILE_CONTAINS = "MyDistro"
            CHECK_FILE_DISTRO_NAME = "mydistro"

        self.assertIsNone(MyProbe().name_for_file_contains())

    def test_name_for_file_contains_ioerror(self):
        class MyProbe(distro.Probe):
            CHECK_FILE = "/etc/fake-release"
            CHECK_FILE_CONTAINS = "MyDistro"
            CHECK_FILE_DISTRO_NAME = "mydistro"

        with unittest.mock.patch(
            "avocado.utils.distro.os.path.exists", return_value=True
        ):
            with unittest.mock.patch(
                "builtins.open", side_effect=IOError("Permission denied")
            ):
                self.assertIsNone(MyProbe().name_for_file_contains())

    def test_version_from_file(self):
        class MyProbe(distro.Probe):
            CHECK_FILE = "/etc/fake-release"
            CHECK_VERSION_REGEX = re.compile(r"Release (\d+)\.(\d+)")

        with unittest.mock.patch(
            "avocado.utils.distro.os.path.exists", return_value=True
        ):
            with unittest.mock.patch(
                "builtins.open",
                unittest.mock.mock_open(read_data="Release 9.3\n"),
            ):
                self.assertEqual(MyProbe().version(), "9")

    def test_version_no_match(self):
        class MyProbe(distro.Probe):
            CHECK_FILE = "/etc/fake-release"
            CHECK_VERSION_REGEX = re.compile(r"Release (\d+)\.(\d+)")

        with unittest.mock.patch(
            "avocado.utils.distro.os.path.exists", return_value=True
        ):
            with unittest.mock.patch(
                "builtins.open",
                unittest.mock.mock_open(read_data="No version here\n"),
            ):
                self.assertEqual(MyProbe().version(), distro.UNKNOWN_DISTRO_VERSION)

    def test_release_from_file(self):
        class MyProbe(distro.Probe):
            CHECK_FILE = "/etc/fake-release"
            CHECK_VERSION_REGEX = re.compile(r"Release (\d+)\.(\d+)")

        with unittest.mock.patch(
            "avocado.utils.distro.os.path.exists", return_value=True
        ):
            with unittest.mock.patch(
                "builtins.open",
                unittest.mock.mock_open(read_data="Release 9.3\n"),
            ):
                self.assertEqual(MyProbe().release(), "3")

    def test_release_single_group(self):
        class MyProbe(distro.Probe):
            CHECK_FILE = "/etc/fake-release"
            CHECK_VERSION_REGEX = re.compile(r"Release (\d+)")

        with unittest.mock.patch(
            "avocado.utils.distro.os.path.exists", return_value=True
        ):
            with unittest.mock.patch(
                "builtins.open",
                unittest.mock.mock_open(read_data="Release 9\n"),
            ):
                self.assertEqual(MyProbe().release(), distro.UNKNOWN_DISTRO_RELEASE)

    def test_check_release_single_group(self):
        class MyProbe(distro.Probe):
            CHECK_FILE = "/etc/fake-release"
            CHECK_VERSION_REGEX = re.compile(r"Release (\d+)")

        self.assertFalse(MyProbe().check_release())

    def test_get_distro_detected(self):
        fd, tmpfile = tempfile.mkstemp(suffix="-release")
        with os.fdopen(fd, "w") as tmp:
            tmp.write("TestDistro release 5.2 (Final)\n")
        self.addCleanup(os.unlink, tmpfile)

        class MyProbe(distro.Probe):
            CHECK_FILE = tmpfile
            CHECK_FILE_CONTAINS = "TestDistro"
            CHECK_FILE_DISTRO_NAME = "testdistro"
            CHECK_VERSION_REGEX = re.compile(r"TestDistro release (\d+)\.(\d+).*")

        result = MyProbe().get_distro()
        self.assertEqual(result.name, "testdistro")
        self.assertEqual(result.version, "5")
        self.assertEqual(result.release, "2")

    def test_get_distro_unknown(self):
        result = distro.Probe().get_distro()
        self.assertIs(result, distro.UNKNOWN_DISTRO)

    def test_check_for_remote_file_found(self):
        mock_session = unittest.mock.MagicMock()
        mock_session.cmd.return_value.exit_status = 0
        probe = distro.Probe(session=mock_session)
        self.assertTrue(probe.check_for_remote_file("/etc/some-file"))
        mock_session.cmd.assert_called_once_with("test -f /etc/some-file")

    def test_check_for_remote_file_not_found(self):
        mock_session = unittest.mock.MagicMock()
        mock_session.cmd.return_value.exit_status = 1
        probe = distro.Probe(session=mock_session)
        self.assertFalse(probe.check_for_remote_file("/etc/nonexistent"))


class ProbeRegexTest(unittest.TestCase):
    """Tests version regex patterns against real release file strings."""

    def test_redhat_regex(self):
        match = distro.RedHatProbe.CHECK_VERSION_REGEX.match(
            "Red Hat Enterprise Linux Server release 9.3 (Plow)"
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "9")
        self.assertEqual(match.group(2), "3")

    def test_centos_stream_regex(self):
        match = distro.CentosStreamProbe.CHECK_VERSION_REGEX.match(
            "CentOS Stream release 9"
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "9")

    def test_debian_numeric_version(self):
        match = distro.DebianProbe.CHECK_VERSION_REGEX.match("12.7")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(2), "12")

    def test_debian_codename_version(self):
        match = distro.DebianProbe.CHECK_VERSION_REGEX.match("trixie/sid")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "sid")

    def test_ubuntu_regex(self):
        content = 'NAME="Ubuntu"\nVERSION_ID="22.04"\nID=ubuntu\n'
        match = distro.UbuntuProbe.CHECK_VERSION_REGEX.match(content)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "22.04")

    def test_amazon_regex(self):
        content = 'NAME="Amazon Linux"\nVERSION="2"\nVERSION_ID="2"\n'
        match = distro.AmazonLinuxProbe.CHECK_VERSION_REGEX.match(content)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "2")


class SUSEProbeTest(unittest.TestCase):
    def test_suse_version_parsing(self):
        os_release = (
            'NAME="SUSE Linux Enterprise Server"\n'
            'VERSION="12-SP2"\n'
            'VERSION_ID="12.2"\n'
            'ID="sles"\n'
        )
        fd, tmpfile = tempfile.mkstemp(suffix="-os-release")
        with os.fdopen(fd, "w") as tmp:
            tmp.write(os_release)
        self.addCleanup(os.unlink, tmpfile)

        with unittest.mock.patch.object(distro.SUSEProbe, "CHECK_FILE", tmpfile):
            result = distro.SUSEProbe().get_distro()
            self.assertEqual(result.name, "SuSE")
            self.assertEqual(result.version, 12)
            self.assertEqual(result.release, 2)


class RegisterProbeTest(unittest.TestCase):
    def setUp(self):
        self._original_probes = distro.REGISTERED_PROBES[:]

    def tearDown(self):
        distro.REGISTERED_PROBES[:] = self._original_probes

    def test_register_new_probe(self):
        class CustomProbe(distro.Probe):
            CHECK_FILE = "/etc/custom-release"

        initial_count = len(distro.REGISTERED_PROBES)
        distro.register_probe(CustomProbe)
        self.assertEqual(len(distro.REGISTERED_PROBES), initial_count + 1)
        self.assertIn(CustomProbe, distro.REGISTERED_PROBES)

    def test_register_duplicate_ignored(self):
        class CustomProbe(distro.Probe):
            CHECK_FILE = "/etc/custom-release"

        distro.register_probe(CustomProbe)
        count_after_first = len(distro.REGISTERED_PROBES)
        distro.register_probe(CustomProbe)
        self.assertEqual(len(distro.REGISTERED_PROBES), count_after_first)


class DetectTest(unittest.TestCase):
    def setUp(self):
        self._original_probes = distro.REGISTERED_PROBES[:]

    def tearDown(self):
        distro.REGISTERED_PROBES[:] = self._original_probes

    def test_detect_returns_best_scoring(self):
        fd, tmpfile = tempfile.mkstemp(suffix="-release")
        with os.fdopen(fd, "w") as tmp:
            tmp.write("HighScore release 3.1\n")
        self.addCleanup(os.unlink, tmpfile)

        class LowProbe(distro.Probe):
            CHECK_FILE = tmpfile
            CHECK_FILE_DISTRO_NAME = "lowscore"

        class HighProbe(distro.Probe):
            CHECK_FILE = tmpfile
            CHECK_FILE_CONTAINS = "HighScore"
            CHECK_FILE_DISTRO_NAME = "highscore"
            CHECK_VERSION_REGEX = re.compile(r"HighScore release (\d+)\.(\d+).*")

        distro.REGISTERED_PROBES[:] = [LowProbe, HighProbe]
        result = distro.detect()
        self.assertEqual(result.name, "highscore")
        self.assertEqual(result.version, "3")
        self.assertEqual(result.release, "1")

    def test_detect_no_probes_returns_unknown(self):
        distro.REGISTERED_PROBES[:] = []
        result = distro.detect()
        self.assertIs(result, distro.UNKNOWN_DISTRO)


class SpecTest(unittest.TestCase):
    def test_init_with_all_args(self):
        spec = distro.Spec("fedora", min_version=38, min_release=0, arch="x86_64")
        self.assertEqual(spec.name, "fedora")
        self.assertEqual(spec.min_version, 38)
        self.assertEqual(spec.min_release, 0)
        self.assertEqual(spec.arch, "x86_64")

    def test_init_defaults(self):
        spec = distro.Spec("rhel")
        self.assertEqual(spec.name, "rhel")
        self.assertIsNone(spec.min_version)
        self.assertIsNone(spec.min_release)
        self.assertIsNone(spec.arch)


if __name__ == "__main__":
    unittest.main()
