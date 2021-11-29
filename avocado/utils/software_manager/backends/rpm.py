import logging
import os
import re

from avocado.utils import path as utils_path
from avocado.utils import process
from avocado.utils.software_manager.backends.base import BaseBackend

LOG = logging.getLogger(__name__)


class RpmBackend(BaseBackend):

    """
    This class implements operations executed with the rpm package manager.

    rpm is a lower level package manager, used by higher level managers such
    as yum and zypper.
    """

    PACKAGE_TYPE = 'rpm'
    SOFTWARE_COMPONENT_QRY = (
        PACKAGE_TYPE + ' ' +
        '%{NAME} %{VERSION} %{RELEASE} %{SIGMD5} %{ARCH}')

    def __init__(self):
        self.lowlevel_base_cmd = utils_path.find_command('rpm')

    def _check_installed_version(self, name, version):
        """
        Helper for the check_installed public method.

        :param name: Package name.
        :param version: Package version.
        """
        cmd = (self.lowlevel_base_cmd + ' -q --qf %{VERSION} ' + name)
        inst_version = process.run(cmd, ignore_status=True).stdout_text

        if 'not installed' in inst_version:
            return False

        return bool(inst_version >= version)

    def check_installed(self, name, version=None, arch=None):
        """
        Check if package [name] is installed.

        :param name: Package name.
        :param version: Package version.
        :param arch: Package architecture.
        """
        if arch:
            cmd = (self.lowlevel_base_cmd + ' -q --qf %{ARCH} ' + name)
            inst_archs = process.system_output(cmd, ignore_status=True)
            inst_archs = inst_archs.split('\n')

            for inst_arch in inst_archs:
                if inst_arch == arch:
                    return self._check_installed_version(name, version)
            return False

        elif version:
            return self._check_installed_version(name, version)
        else:
            cmd = 'rpm -q ' + name
            try:
                process.system(cmd)
                return True
            except process.CmdError:
                return False

    def list_all(self, software_components=True):
        """
        List all installed packages.

        :param software_components: log in a format suitable for the
                                    SoftwareComponent schema
        """
        LOG.debug("Listing all system packages (may take a while)")

        if software_components:
            cmd_format = "rpm -qa --qf '%s' | sort"
            query_format = "%s\n" % self.SOFTWARE_COMPONENT_QRY
            cmd_format %= query_format
            cmd_result = process.run(cmd_format, verbose=False, shell=True)
        else:
            cmd_result = process.run('rpm -qa | sort', verbose=False,
                                     shell=True)

        out = cmd_result.stdout_text.strip()
        installed_packages = out.splitlines()
        return installed_packages

    @staticmethod
    def list_files(name):
        """
        List files installed on the system by package [name].

        :param name: Package name.
        """
        path = os.path.abspath(name)
        if os.path.isfile(path):
            option = '-qlp'
            name = path
        else:
            option = '-ql'

        l_cmd = 'rpm' + ' ' + option + ' ' + name

        try:
            result = process.system_output(l_cmd)
            list_files = result.split('\n')
            return list_files
        except process.CmdError:
            return []

    @staticmethod
    def rpm_install(file_path, no_dependencies=False, replace=False):
        """
        Install the rpm file [file_path] provided.

        :param str file_path: file path of the installed package
        :param bool no_dependencies: whether to add "nodeps" flag
        :param bool replace: whether to replace existing package
        :returns: whether file is installed properly
        :rtype: bool
        """
        if not os.path.isfile(file_path):
            LOG.warning('Please provide proper rpm path')
            return False

        nodeps = "--nodeps " if no_dependencies else ""
        update = "-U" if replace else "-i"
        cmd = "rpm %s %s%s" % (update, nodeps, file_path)

        try:
            process.system(cmd)
            return True
        except process.CmdError as details:
            LOG.error(details)
            return False

    @staticmethod
    def rpm_verify(package_name):
        """
        Verify an RPM package with an installed one.

        :param str package_name: name of the verified package
        :returns: whether the verification was successful
        :rtype: bool
        """
        LOG.info("Verifying package information.")
        cmd = "rpm -V " + package_name
        result = process.run(cmd, ignore_status=True)

        # unstable approach but currently works
        # installed_pattern = r"\s" + package_name + r" is installed\s+"
        # match = re.search(installed_pattern, result)
        match = (result.exit_status == 0)
        if match:
            LOG.info("Verification successful.")
            return True
        else:
            LOG.info(result.stdout_text.rstrip())
            return False

    @staticmethod
    def rpm_erase(package_name):
        """
        Erase an RPM package.

        :param str package_name: name of the erased package
        :returns: whether file is erased properly
        :rtype: bool
        """
        LOG.warning("Erasing rpm package %s", package_name)
        cmd = "rpm -e " + package_name
        result = process.run(cmd, ignore_status=True)
        if result.exit_status:
            return False
        return True

    @staticmethod
    def prepare_source(spec_file, dest_path=None):
        """
        Rpmbuild the spec path and return build dir

        :param spec_path: spec path to install
        :return path: build directory
        """

        build_option = "-bp"
        if dest_path is not None:
            build_option += " --define '_builddir %s'" % dest_path
        else:
            LOG.error("Please provide a valid path")
            return ""
        try:
            process.system("rpmbuild %s %s" % (build_option, spec_file))
            return os.path.join(dest_path, os.listdir(dest_path)[0])
        except process.CmdError as details:
            LOG.error(details)
            return ""

    def find_rpm_packages(self, rpm_dir):
        """
        Extract product dependencies from a defined RPM directory and all its subdirectories.

        :param str rpm_dir: directory to search in
        :returns: found RPM packages
        :rtype: [str]
        """
        subpaths = os.listdir(rpm_dir)
        subpacks = []
        for subpath in subpaths:
            if subpath == "." or subpath == "..":
                continue
            new_filepath = rpm_dir + "/" + subpath
            LOG.debug("Checking path for rpm %s", new_filepath)
            # if path is file validate name and inject
            if os.path.isfile(new_filepath) and re.search(r"\s*.rpm$", os.path.basename(new_filepath)):
                LOG.info("Marking package %s for setup", new_filepath)
                subpacks.append(new_filepath)
            elif os.path.isdir(new_filepath):
                subpacks += self.find_rpm_packages(new_filepath)
        return subpacks

    @staticmethod
    def is_valid(package_path):
        """Verifies if a package is a valid rpm file.

        :param str package_path: .rpm package path.
        :returns: True if valid, otherwise false.
        :rtype: bool
        """
        abs_path = os.path.abspath(os.path.expanduser((package_path)))
        try:
            result = process.run("rpm -qp {}".format(abs_path))
        except process.CmdError:
            return False
        if result.exit_status == 0:
            return True
        return False

    @staticmethod
    def extract_from_package(package_path, dest_path=None):
        """Extracts the package content to a specific destination path.

        :param str package_path: path to the rpm package.
        :param dest_path: destination path to extract the files. Default it
                          will be the current directory.
        :returns: path of the extracted file
        :returns: the path of the extracted files.
        :rtype: str
        """
        abs_path = os.path.abspath(os.path.expanduser(package_path))
        dest = dest_path or os.path.curdir

        # If something goes wrong process.run will raise a CmdError exception
        process.run("rpm2cpio {} | cpio -dium -D {}".format(abs_path,
                                                            dest),
                    shell=True)
        return dest

    def perform_setup(self, packages, no_dependencies=False):
        """
        General RPM setup with automatic handling of dependencies based on
        install attempts.

        :param packages: the RPM packages to install in dependency-friendly order
        :type packages: [str]
        :returns: whether setup completed successfully
        :rtype: bool
        """
        while len(packages) > 0:
            LOG.debug("Trying to install: %s", packages)
            failed_packages = []
            for package_path in packages:
                package_file = os.path.basename(package_path)
                package_name = "-".join(package_file.split('-')[0:-2])
                LOG.debug("%s -> %s", package_file, package_name)
                installed = self.check_installed(package_name)
                verified = self.rpm_verify(package_name) if installed else False
                if installed and not verified:
                    self.rpm_erase(package_name)
                if not installed or not verified:
                    success = self.rpm_install(package_path, no_dependencies)
                    if not success:
                        failed_packages.append(package_path)
            if len(packages) == len(failed_packages) > 0:
                LOG.warning("Some of the rpm packages could not be "
                            "installed: %s", ", ".join(failed_packages))
                return False
            packages = failed_packages
        return True
