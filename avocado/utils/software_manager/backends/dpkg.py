import io
import logging
import os
import re
import tarfile

from avocado.utils import ar
from avocado.utils import path as utils_path
from avocado.utils import process
from avocado.utils.software_manager.backends.base import BaseBackend

log = logging.getLogger('avocado.utils.software_manager')


class DpkgBackend(BaseBackend):

    """
    This class implements operations executed with the dpkg package manager.

    dpkg is a lower level package manager, used by higher level managers such
    as apt and aptitude.
    """

    PACKAGE_TYPE = 'deb'
    INSTALLED_OUTPUT = 'install ok installed'

    def __init__(self):
        self.lowlevel_base_cmd = utils_path.find_command('dpkg')

    def check_installed(self, name):
        if os.path.isfile(name):
            n_cmd = self.lowlevel_base_cmd + ' -f ' + name + ' Package'
            name = process.system_output(n_cmd)
        i_cmd = self.lowlevel_base_cmd + " -s " + name
        # Checking if package is installed
        package_status = process.run(i_cmd, ignore_status=True).stdout_text
        dpkg_installed = (self.INSTALLED_OUTPUT in package_status)
        if dpkg_installed:
            return True
        return False

    @staticmethod
    def list_all():
        """
        List all packages available in the system.
        """
        log.debug("Listing all system packages (may take a while)")
        installed_packages = []
        cmd_result = process.run('dpkg -l', verbose=False)
        out = cmd_result.stdout_text.strip()
        raw_list = out.splitlines()[5:]
        for line in raw_list:
            parts = line.split()
            if parts[0] == "ii":  # only grab "installed" packages
                installed_packages.append("%s-%s" % (parts[1], parts[2]))
        return installed_packages

    @staticmethod
    def is_valid(package_path):
        """Verifies if a package is a valid deb file.

        :param str package_path: .deb package path.
        :returns: True if valid, otherwise false.
        :rtype: bool
        """
        abs_path = os.path.abspath(os.path.expanduser((package_path)))
        member_regexes = [r'debian-binary',
                          r'control\.tar\..*',
                          r'data\.tar\..*']
        members = ar.Ar(abs_path).list()
        if len(members) != len(member_regexes):
            return False
        for regex, member in zip(member_regexes, members):
            if not re.match(regex, member):
                return False
        return True

    @staticmethod
    def extract_from_package(package_path, dest_path=None):
        """Extracts the package content to a specific destination path.

        :param str package_path: path to the deb package.
        :param dest_path: destination path to extract the files. Default is the
                          current directory.
        :returns: path of the extracted file
        :returns: the path of the extracted files.
        :rtype: str
        """
        abs_path = os.path.abspath(os.path.expanduser(package_path))
        dest = dest_path or os.path.curdir
        os.makedirs(dest, exist_ok=True)
        archive = ar.Ar(abs_path)
        data_tarball_name = archive.list()[2]
        member_data = archive.read_member(data_tarball_name)
        tarball = tarfile.open(fileobj=io.BytesIO(member_data))
        tarball.extractall(dest)
        return dest

    def list_files(self, package):
        """
        List files installed by package [package].

        :param package: Package name.
        :return: List of paths installed by package.
        """
        if os.path.isfile(package):
            l_cmd = self.lowlevel_base_cmd + ' -c ' + package
        else:
            l_cmd = self.lowlevel_base_cmd + ' -l ' + package
        return process.system_output(l_cmd).split('\n')
