# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""Detect the Linux distribution running on a local or remote machine."""

import logging
import os
import platform
import re

LOGGER = logging.getLogger(__name__)

__all__ = [
    "LinuxDistro",
    "UNKNOWN_DISTRO_NAME",
    "UNKNOWN_DISTRO_VERSION",
    "UNKNOWN_DISTRO_RELEASE",
    "UNKNOWN_DISTRO_ARCH",
    "Probe",
    "register_probe",
    "detect",
]


# pylint: disable=R0903
class LinuxDistro:
    """Simple collection of information for a Linux Distribution."""

    def __init__(self, name, version, release, arch):
        """Initialize a new Linux Distro.

        :param name: a short name that precisely distinguishes this Linux
                     Distribution among all others.
        :type name: str
        :param version: the major version of the distribution. Usually this
                        is a single number that denotes a large development
                        cycle and support file.
        :type version: str
        :param release: the release or minor version of the distribution.
                        Usually this is also a single number, that is often
                        omitted or starts with a 0 when the major version
                        is initially release. It's often associated with a
                        shorter development cycle that contains incremental
                        a collection of improvements and fixes.
        :type release: str
        :param arch: the main target for this Linux Distribution. It's common
                     for some architectures to ship with packages for
                     previous and still compatible architectures, such as it's
                     the case with Intel/AMD 64 bit architecture that support
                     32 bit code. In cases like this, this should be set to
                     the 64 bit architecture name.
        :type arch: str
        """
        self.name = name
        self.version = version
        self.release = release
        self.arch = arch

    def __repr__(self):
        """Return a string representation of the Linux distro.

        :return: formatted string with name, version, release and arch.
        :rtype: str
        """
        return (
            f"<LinuxDistro: name={self.name}, version={self.version}, "
            f"release={self.release}, arch={self.arch}>"
        )


UNKNOWN_DISTRO_NAME = "unknown"
UNKNOWN_DISTRO_VERSION = 0
UNKNOWN_DISTRO_RELEASE = 0
UNKNOWN_DISTRO_ARCH = "unknown"


#: The distribution that is used when the exact one could not be found
UNKNOWN_DISTRO = LinuxDistro(
    UNKNOWN_DISTRO_NAME,
    UNKNOWN_DISTRO_VERSION,
    UNKNOWN_DISTRO_RELEASE,
    UNKNOWN_DISTRO_ARCH,
)


class Probe:
    """Probe a machine to confirm which Linux distribution it runs.

    If given an avocado.utils.ssh.Session object representing another machine,
    Probe will attempt to detect that machine's distro via an ssh connection.
    """

    #: Points to a file that can determine if this machine is running a given
    #: Linux Distribution. This servers a first check that enables the extra
    #: checks to carry on.
    CHECK_FILE = None

    #: Sets the content that should be checked on the file pointed to by
    #: :attr:`CHECK_FILE_EXISTS`. Leave it set to `None` (its default)
    #: to check only if the file exists, and not check its contents
    CHECK_FILE_CONTAINS = None

    #: The name of the Linux Distribution to be returned if the file defined
    #: by :attr:`CHECK_FILE_EXISTS` exist.
    CHECK_FILE_DISTRO_NAME = None

    #: A regular expression that will be run on the file pointed to by
    #: :attr:`CHECK_FILE_EXISTS`
    CHECK_VERSION_REGEX = None

    def __init__(self, session=None):
        """Initialize a Probe instance.

        :param session: optional ssh session to probe a remote machine.
        :type session: avocado.utils.ssh.Session or None
        """
        self.score = 0
        self.session = session

    def check_for_remote_file(self, file_name):
        """Check if a file exists on a remote machine.

        :param file_name: path to the file on the remote machine.
        :type file_name: str
        :return: whether the file exists on the remote machine.
        :rtype: bool
        """
        if self.session and not self.session.cmd(f"test -f {file_name}").exit_status:
            return True
        return False

    def check_name_for_file(self):
        """Check if this class can look for a file and return a distro name.

        The conditions that must be true include the file that identifies the
        distro file being set (:attr:`CHECK_FILE`) and the name of the
        distro to be returned (:attr:`CHECK_FILE_DISTRO_NAME`).

        :return: whether both CHECK_FILE and CHECK_FILE_DISTRO_NAME are set.
        :rtype: bool
        """
        if self.CHECK_FILE is None:
            return False

        if self.CHECK_FILE_DISTRO_NAME is None:
            return False

        return True

    def name_for_file(self):
        """Get the distro name if :attr:`CHECK_FILE` is set and exists.

        :return: the distro name or None if the file does not exist.
        :rtype: str or None
        """
        if self.check_name_for_file():
            if self.check_for_remote_file(self.CHECK_FILE):
                return self.CHECK_FILE_DISTRO_NAME
            if os.path.exists(self.CHECK_FILE):
                return self.CHECK_FILE_DISTRO_NAME
        return None

    def check_name_for_file_contains(self):
        """Check if this class can search file content and return a distro.

        The conditions that must be true include the file that identifies the
        distro file being set (:attr:`CHECK_FILE`), the text to look for
        inside the distro file (:attr:`CHECK_FILE_CONTAINS`) and the name
        of the distro to be returned (:attr:`CHECK_FILE_DISTRO_NAME`).

        :return: whether CHECK_FILE, CHECK_FILE_CONTAINS and
                 CHECK_FILE_DISTRO_NAME are all set.
        :rtype: bool
        """
        if self.CHECK_FILE is None:
            return False

        if self.CHECK_FILE_CONTAINS is None:
            return False

        if self.CHECK_FILE_DISTRO_NAME is None:
            return False

        return True

    def name_for_file_contains(self):
        """Get the distro if :attr:`CHECK_FILE` contains expected text.

        :return: the distro name or None if the text is not found.
        :rtype: str or None
        """
        if self.check_name_for_file_contains():
            check_file = None
            if self.check_for_remote_file(self.CHECK_FILE):
                check_file = self.session.cmd(
                    f"cat {self.CHECK_FILE}"
                ).stdout_text.split("/n")
            elif os.path.exists(self.CHECK_FILE):
                try:
                    # pylint: disable=R1732
                    check_file = open(self.CHECK_FILE, encoding="utf-8")
                except IOError as err:
                    LOGGER.debug("Could not open %s", self.CHECK_FILE)
                    LOGGER.debug("Exception: %s", str(err))
                    return None

            if not check_file:
                return None

            for line in check_file:
                if self.CHECK_FILE_CONTAINS in line:
                    return self.CHECK_FILE_DISTRO_NAME
        return None

    def check_version(self):
        """Check if this class can extract a version via regex.

        :return: whether both CHECK_FILE and CHECK_VERSION_REGEX are set.
        :rtype: bool
        """
        if self.CHECK_FILE is None:
            return False

        if self.CHECK_VERSION_REGEX is None:
            return False

        return True

    def _get_version_match(self):
        """Return the regex match result for the version file content.

        :return: the regex match object, or None if no match or file
                 is unavailable.
        :rtype: re.Match or None
        """
        if self.check_version():
            if self.session:
                if self.session.cmd(f"test -f {self.CHECK_FILE}").exit_status:
                    return None
            elif not os.path.exists(self.CHECK_FILE):
                return None

            version_file_content = None
            if self.session:
                version_file_content = self.session.cmd(
                    f"cat {self.CHECK_FILE}"
                ).stdout_text
            else:
                try:
                    with open(self.CHECK_FILE, encoding="utf-8") as check_file:
                        version_file_content = check_file.read()
                except IOError as err:
                    LOGGER.debug("Could not open %s", self.CHECK_FILE)
                    LOGGER.debug("Exception: %s", str(err))
                    return None

            return self.CHECK_VERSION_REGEX.match(version_file_content)
        return None

    def version(self):
        """Return the version of the distro.

        :return: the version string, or UNKNOWN_DISTRO_VERSION.
        :rtype: str or int
        """
        version = UNKNOWN_DISTRO_VERSION
        match = self._get_version_match()
        if match is not None:
            if len(match.groups()) > 0:
                version = match.groups()[0]
        return version

    def check_release(self):
        """Check if the regex has enough groups to extract a release number.

        :return: whether a release can be extracted from the version regex.
        :rtype: bool
        """
        return self.check_version() and self.CHECK_VERSION_REGEX.groups > 1

    def release(self):
        """Return the release of the distro.

        :return: the release string, or UNKNOWN_DISTRO_RELEASE.
        :rtype: str or int
        """
        release = UNKNOWN_DISTRO_RELEASE
        match = self._get_version_match()
        if match is not None:
            if len(match.groups()) > 1:
                if match.groups()[1]:
                    release = match.groups()[1]
        return release

    def get_distro(self):
        """Run all configured checks and return the detected distro.

        :return: the detected :class:`LinuxDistro` or :data:`UNKNOWN_DISTRO`.
        :rtype: :class:`LinuxDistro`
        """
        name = None
        version = UNKNOWN_DISTRO_VERSION
        release = UNKNOWN_DISTRO_RELEASE

        distro = None

        if self.check_name_for_file():
            name = self.name_for_file()
            self.score += 1

        if self.check_name_for_file_contains():
            name = self.name_for_file_contains()
            self.score += 1

        if self.check_version():
            version = self.version()
            self.score += 1

        if self.check_release():
            release = self.release()
            self.score += 1

        if self.session:
            arch = self.session.cmd("uname -m").stdout_text
        else:
            arch = platform.machine()

        # name is the first thing that should be identified. If we don't know
        # the distro name, we don't bother checking for versions
        if name is not None:
            distro = LinuxDistro(name, version, release, arch)
        else:
            distro = UNKNOWN_DISTRO

        return distro


class RedHatProbe(Probe):
    """Probe with version checks for Red Hat Enterprise Linux systems."""

    CHECK_FILE = "/etc/redhat-release"
    CHECK_FILE_CONTAINS = "Red Hat Enterprise Linux"
    CHECK_FILE_DISTRO_NAME = "rhel"
    CHECK_VERSION_REGEX = re.compile(
        r"Red Hat Enterprise Linux\s+\w*\s*release\s+(\d{1,2})\.(\d{1,2}).*"
    )


class CentosProbe(RedHatProbe):
    """Probe with version checks for CentOS systems."""

    CHECK_FILE = "/etc/redhat-release"
    CHECK_FILE_CONTAINS = "CentOS Linux"
    CHECK_FILE_DISTRO_NAME = "centos"
    CHECK_VERSION_REGEX = re.compile(r"CentOS Linux release (\d{1,2})\.(\d{1,2}).*")


class CentosStreamProbe(RedHatProbe):
    """Probe with version checks for CentOS Stream systems."""

    CHECK_FILE = "/etc/redhat-release"
    CHECK_FILE_CONTAINS = "CentOS Stream"
    CHECK_FILE_DISTRO_NAME = "centos-stream"
    CHECK_VERSION_REGEX = re.compile(r"CentOS Stream release (\d{1,2})")


class FedoraProbe(RedHatProbe):
    """Probe with version checks for Fedora systems."""

    CHECK_FILE = "/etc/fedora-release"
    CHECK_FILE_CONTAINS = "Fedora"
    CHECK_FILE_DISTRO_NAME = "fedora"
    CHECK_VERSION_REGEX = re.compile(r"Fedora release (\d{1,2}).*")


class AmazonLinuxProbe(Probe):
    """Probe for Amazon Linux systems."""

    CHECK_FILE = "/etc/os-release"
    CHECK_FILE_CONTAINS = "Amazon Linux"
    CHECK_FILE_DISTRO_NAME = "amzn"
    CHECK_VERSION_REGEX = re.compile(
        r".*VERSION=\"(\d+)\.?(\d+)?\".*", re.MULTILINE | re.DOTALL
    )


class DebianProbe(Probe):
    """Probe with file checks for Debian systems."""

    CHECK_FILE = "/etc/debian_version"
    CHECK_FILE_DISTRO_NAME = "debian"
    CHECK_VERSION_REGEX = re.compile(r".+/(.+)|(\d+)\.\d+")


class UbuntuProbe(Probe):
    """Probe for Ubuntu systems."""

    CHECK_FILE = "/etc/os-release"
    CHECK_FILE_CONTAINS = "ubuntu"
    CHECK_FILE_DISTRO_NAME = "Ubuntu"
    CHECK_VERSION_REGEX = re.compile(
        r".*VERSION_ID=\"(\d+\.\d+)\".*", re.MULTILINE | re.DOTALL
    )


class SUSEProbe(Probe):
    """Probe for SUSE systems with custom VERSION_ID parsing."""

    CHECK_FILE = "/etc/os-release"
    CHECK_FILE_CONTAINS = "SUSE"
    # this is the (incorrect) spelling used in python's platform
    # and tests are looking for it in distro.name. So keep using it
    CHECK_FILE_DISTRO_NAME = "SuSE"

    def get_distro(self):
        """Detect SUSE distro and parse VERSION_ID for version and release.

        :return: the detected :class:`LinuxDistro` with parsed version.
        :rtype: :class:`LinuxDistro`
        """
        distro = super().get_distro()

        # if the default methods find SUSE, detect version
        if not distro.name == self.CHECK_FILE_DISTRO_NAME:
            return distro

        # we need to check VERSION_ID, which is number - VERSION can
        # be a string

        # for openSUSE Tumbleweed this will be e.g. 20161225
        # for openSUSE Leap this will be e.g. 42.2
        # for SUSE Linux Enterprise this will be e.g. 12 or 12.2 (for SP2)
        version_id_re = re.compile(r'VERSION_ID="([\d\.]*)"')
        version_id = None

        with open(self.CHECK_FILE, encoding="utf-8") as check_file:
            for line in check_file:
                match = version_id_re.match(line)
                if match:
                    version_id = match.group(1)

        if version_id:
            version_parts = version_id.split(".")
            distro.version = int(version_parts[0])
            if len(version_parts) > 1:
                distro.release = int(version_parts[1])

        return distro


class OpenEulerProbe(Probe):
    """Probe for openEuler systems."""

    CHECK_FILE = "/etc/openEuler-release"
    CHECK_FILE_CONTAINS = "openEuler release"
    CHECK_FILE_DISTRO_NAME = "openEuler"
    CHECK_VERSION_REGEX = re.compile(r"openEuler release (\d+)\.(\d+).*")


class UnionTechProbe(Probe):
    """Probe for UnionTech OS systems."""

    CHECK_FILE = "/etc/os-version"
    CHECK_FILE_CONTAINS = "UnionTech OS"
    CHECK_FILE_DISTRO_NAME = "uos"
    CHECK_VERSION_REGEX = re.compile(r"MinorVersion=(\d+)")


#: the complete list of probes that have been registered
REGISTERED_PROBES = []


def register_probe(probe_class):
    """Register a probe to be run during autodetection.

    :param probe_class: the probe class to register.
    :type probe_class: type
    """
    if probe_class not in REGISTERED_PROBES:
        REGISTERED_PROBES.append(probe_class)


register_probe(RedHatProbe)
register_probe(CentosProbe)
register_probe(CentosStreamProbe)
register_probe(FedoraProbe)
register_probe(AmazonLinuxProbe)
register_probe(DebianProbe)
register_probe(SUSEProbe)
register_probe(UbuntuProbe)
register_probe(OpenEulerProbe)
register_probe(UnionTechProbe)


def detect(session=None):
    """Attempt to detect the Linux distribution running on this machine.

    If given an avocado.utils.ssh.Session object, it will attempt to detect
    the distro of another machine via an ssh connection.

    :param session: ssh connection to another machine.
    :type session: avocado.utils.ssh.Session or None
    :return: the detected :class:`LinuxDistro` or :data:`UNKNOWN_DISTRO`.
    :rtype: :class:`LinuxDistro`
    """
    results = []

    for probe_class in REGISTERED_PROBES:
        probe_instance = probe_class(session)
        distro_result = probe_instance.get_distro()
        if distro_result is not UNKNOWN_DISTRO:
            results.append((distro_result, probe_instance))

    results.sort(key=lambda t: t[1].score)
    if len(results) > 0:
        distro = results[-1][0]
    else:
        distro = UNKNOWN_DISTRO

    return distro


class Spec:
    """Describe a distro, usually for setting minimum distro requirements."""

    def __init__(self, name, min_version=None, min_release=None, arch=None):
        """Initialize a distro specification.

        :param name: the distribution name to match.
        :type name: str
        :param min_version: minimum acceptable version.
        :type min_version: int or None
        :param min_release: minimum acceptable release.
        :type min_release: int or None
        :param arch: required architecture.
        :type arch: str or None
        """
        self.name = name
        self.min_version = min_version
        self.min_release = min_release
        self.arch = arch


# pylint: disable=wrong-import-position
from avocado.utils.deprecation import log_deprecation

log_deprecation.warning("distro")
