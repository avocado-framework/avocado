import logging
import os
import re

from ... import path as utils_path
from ... import process
from .base import BaseBackend

log = logging.getLogger('avocado.utils.software_manager')


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

    def __init__(self, session=None):
        """
        Initializes the base command.

        :param session: ssh connection to get the base command of another machine
        :type session: avocado.utils.ssh.Session
        """
        self.lowlevel_base_cmd = utils_path.find_command('rpm',
                                                         session=session)
        self.session = session

    def _check_installed_version(self, name, version):
        """
        Helper for the check_installed public method.

        :param name: Package name.
        :param version: Package version.
        """
        cmd = (self.lowlevel_base_cmd + ' -q --qf %{VERSION} ' + name)
        if self.session:
            inst_version = self.session.cmd(cmd,
                                            ignore_status=True).stdout_text
        else:
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
            if self.session:
                inst_archs = self.session.cmd(cmd,
                                              ignore_status=True).stdout_text
            else:
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
                if self.session:
                    self.session.cmd(cmd)
                else:
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
        log.debug("Listing all system packages (may take a while)")

        if software_components:
            cmd_format = "rpm -qa --qf '%s' | sort"
            query_format = "%s\n" % self.SOFTWARE_COMPONENT_QRY
            cmd_format %= query_format
            if self.session:
                cmd_result = self.session.cmd(cmd_format)
            else:
                cmd_result = process.run(cmd_format, verbose=False, shell=True)
        else:
            cmd = 'rpm -qa | sort'
            if self.session:
                cmd_result = self.session.cmd(cmd)
            else:
                cmd_result = process.run(cmd,
                                         verbose=False,
                                         shell=True)

        out = cmd_result.stdout_text.strip()
        installed_packages = out.splitlines()
        return installed_packages

    @staticmethod
    def list_files(name, session=None):
        """
        List files installed on the system by package [name].

        :param name: Package name.
        :param session: ssh connection that represents another machine
        :type session: avocado.utils.ssh.Session
        """
        if session:
            path = session.cmd("realpath %s" % name).stdout_text.rstrip()
            if session.cmd("test -f %s" % path).exit_status == 0:
                option = '-qlp'
                name = path
            else:
                option = '-ql'
        else:
            path = os.path.abspath(name)
            if os.path.isfile(path):
                option = '-qlp'
                name = path
            else:
                option = '-ql'

        l_cmd = 'rpm' + ' ' + option + ' ' + name

        try:
            if session:
                result = session.cmd(l_cmd).stdout_text
            else:
                result = process.system_output(l_cmd)
            list_files = result.split('\n')
            return list_files
        except process.CmdError:
            return []

    @staticmethod
    def rpm_install(file_path, no_dependencies=False, replace=False, session=None):
        """
        Install the rpm file [file_path] provided.

        :param str file_path: file path of the installed package
        :param bool no_dependencies: whether to add "nodeps" flag
        :param bool replace: whether to replace existing package
        :param session: ssh connection that represents another machine
        :type session: avocado.utils.ssh.Session
        :returns: whether file is installed properly
        :rtype: bool
        """
        if session and session.cmd("test -f %s" % file_path).exit_status != 0:
            log.warning('Please provide proper rpm path for remote machine')
            return False

        if not os.path.isfile(file_path) and not session:
            log.warning('Please provide proper rpm path')
            return False

        nodeps = "--nodeps " if no_dependencies else ""
        update = "-U" if replace else "-i"
        cmd = "rpm %s %s%s" % (update, nodeps, file_path)

        try:
            if session:
                session.cmd(cmd)
            else:
                process.system(cmd)
            return True
        except process.CmdError as details:
            log.error(details)
            return False

    @staticmethod
    def rpm_verify(package_name, session=None):
        """
        Verify an RPM package with an installed one.

        :param str package_name: name of the verified package
        :param session: ssh connection that represents another machine
        :type session: avocado.utils.ssh.Session
        :returns: whether the verification was successful
        :rtype: bool
        """
        logging.info("Verifying package information.")
        cmd = "rpm -V " + package_name
        if session:
            result = session.cmd(cmd, ignore_status=True)
        else:
            result = process.run(cmd, ignore_status=True)

        # unstable approach but currently works
        # installed_pattern = r"\s" + package_name + r" is installed\s+"
        # match = re.search(installed_pattern, result)
        match = (result.exit_status == 0)
        if match:
            logging.info("Verification successful.")
            return True
        else:
            logging.info(result.stdout_text.rstrip())
            return False

    @staticmethod
    def rpm_erase(package_name, session=None):
        """
        Erase an RPM package.

        :param str package_name: name of the erased package
        :param session: ssh connection that represents another machine
        :type session: avocado.utils.ssh.Session
        :returns: whether file is erased properly
        :rtype: bool
        """
        logging.warning("Erasing rpm package %s", package_name)
        cmd = "rpm -e " + package_name
        if session:
            result = session.cmd(cmd, ignore_status=True)
        else:
            result = process.run(cmd, ignore_status=True)
        if result.exit_status:
            return False
        return True

    @staticmethod
    def prepare_source(spec_file, dest_path=None, session=None):
        """
        Rpmbuild the spec path and return build dir

        :param spec_path: spec path to install
        :param session: ssh connection that represents another machine
        :type session: avocado.utils.ssh.Session
        :return path: build directory
        """

        build_option = "-bp"
        if dest_path is not None:
            build_option += " --define '_builddir %s'" % dest_path
        else:
            log.error("Please provide a valid path")
            return ""
        try:
            cmd = "rpmbuild %s %s" % (build_option, spec_file)
            if session:
                session.cmd(cmd)
                return dest_path
            else:
                process.system(cmd)
                return os.path.join(dest_path, os.listdir(dest_path)[0])
        except process.CmdError as details:
            log.error(details)
            return ""

    def find_rpm_packages(self, rpm_dir):
        """
        Extract product dependencies from a defined RPM directory and all its subdirectories.

        :param str rpm_dir: directory to search in
        :returns: found RPM packages
        :rtype: [str]
        """
        if self.session:
            subpaths = self.session.cmd("ls -a %s" %
                                        rpm_dir).stdout_text.split()
        else:
            subpaths = os.listdir(rpm_dir)
        subpacks = []
        for subpath in subpaths:
            if subpath == "." or subpath == "..":
                continue
            new_filepath = rpm_dir + "/" + subpath
            logging.debug("Checking path for rpm %s", new_filepath)
            # if path is file validate name and inject
            correct_format = re.search(r"\s*.rpm$",
                                       os.path.basename(new_filepath))
            if self.session:
                if self.session.cmd("test -f %s" % new_filepath) and correct_format:
                    logging.info("Marking package %s for setup", new_filepath)
                    subpacks.append(new_filepath)
                elif self.session.cmd("[ -d %s ]" % new_filepath).exit_status == 0:
                    subpacks += self.find_rpm_packages(new_filepath)
            elif os.path.isfile(new_filepath) and correct_format:
                logging.info("Marking package %s for setup", new_filepath)
                subpacks.append(new_filepath)
            elif os.path.isdir(new_filepath):
                subpacks += self.find_rpm_packages(new_filepath)
        return subpacks

    @staticmethod
    def is_valid(package_path, session=None):
        """Verifies if a package is a valid rpm file.

        :param str package_path: .rpm package path.
        :param session: ssh connection that represents another machine
        :type session: avocado.utils.ssh.Session
        :returns: True if valid, otherwise false.
        :rtype: bool
        """
        if session:
            abs_path = session.cmd("realpath %s" % package_path).stdout_text
        else:
            abs_path = os.path.abspath(os.path.expanduser((package_path)))
        try:
            if session:
                result = session.cmd("rpm -qip {}".format(abs_path))
            else:
                result = process.run("rpm -qip {}".format(abs_path))
        except process.CmdError:
            return False
        if result.exit_status == 0:
            return True
        return False

    @staticmethod
    def extract_from_package(package_path, dest_path=None, session=None):
        """Extracts the package content to a specific destination path.

        :param str package_path: path to the rpm package.
        :param dest_path: destination path to extract the files. Default it
                          will be the current directory.
        :param session: ssh connection that represents another machine
        :type session: avocado.utils.ssh.Session
        :returns: path of the extracted file
        :returns: the path of the extracted files.
        :rtype: str
        """
        if session:
            abs_path = session.cmd("realpath %s" % package_path).stdout_text
        else:
            abs_path = os.path.abspath(os.path.expanduser(package_path))
        dest = dest_path or os.path.curdir

        # If something goes wrong process.run will raise a CmdError exception
        if session:
            session.cmd("rpm2cpio {} | cpio -dium -D {}".format(abs_path, dest))
        else:
            process.run("rpm2cpio {} | cpio -dium -D {}".format(abs_path, dest),
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
            logging.debug("Trying to install: %s", packages)
            failed_packages = []
            for package_path in packages:
                package_file = os.path.basename(package_path)
                package_name = "-".join(package_file.split('-')[0:-2])
                logging.debug("%s -> %s", package_file, package_name)
                installed = self.check_installed(package_name)
                verified = self.rpm_verify(
                    package_name) if installed else False
                if installed and not verified:
                    self.rpm_erase(package_name)
                if not installed or not verified:
                    success = self.rpm_install(package_path, no_dependencies)
                    if not success:
                        failed_packages.append(package_path)
            if len(packages) == len(failed_packages) > 0:
                logging.warning(
                    "Some of the rpm packages could not be "
                    "installed: %s", ", ".join(failed_packages))
                return False
            packages = failed_packages
        return True
