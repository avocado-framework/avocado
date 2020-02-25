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
# Copyright: IBM 2008-2009
# Copyright: Red Hat Inc. 2009-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>
# Author: Higor Vieira Alves <halves@br.ibm.com>
# Author: Ramon de Carvalho Valle <rcvalle@br.ibm.com>

#
# This code was adapted from the autotest project,
# client/shared/software_manager.py

"""
Software package management library.

This is an abstraction layer on top of the existing distributions high level
package managers. It supports package operations useful for testing purposes,
and multiple high level package managers (here called backends).
"""
import os
import re
import shutil
import logging
import argparse
import tempfile
import configparser

try:
    import yum
except ImportError:
    HAS_YUM_MODULE = False
else:
    HAS_YUM_MODULE = True

from . import process
from . import data_factory
from . import distro
from . import path as utils_path

log = logging.getLogger('avocado.test')

# If you want to make this lib to support your particular package
# manager/distro, please implement the given backend class and
# update the global SUPPORTED_PACKAGE_MANAGERS variable accordingly.


class SystemInspector:

    """
    System inspector class.

    This may grow up to include more complete reports of operating system and
    machine properties.
    """

    def __init__(self):
        """
        Probe system, and save information for future reference.
        """
        self.distro = distro.detect().name

    def get_package_management(self):
        """
        Determine the supported package management systems present on the
        system. If more than one package management system installed, try
        to find the best supported system.
        """
        list_supported = []
        for high_level_pm in SUPPORTED_PACKAGE_MANAGERS:
            try:
                utils_path.find_command(high_level_pm)
                list_supported.append(high_level_pm)
            except utils_path.CmdNotFoundError:
                pass

        pm_supported = None
        if len(list_supported) == 0:
            pm_supported = None
        if len(list_supported) == 1:
            pm_supported = list_supported[0]
        elif len(list_supported) > 1:
            if ('apt-get' in list_supported and
                    self.distro in ('debian', 'ubuntu')):
                pm_supported = 'apt-get'
            elif ('dnf' in list_supported and
                  self.distro in ('rhel', 'fedora')):
                pm_supported = 'dnf'
            elif ('yum' in list_supported and
                  self.distro in ('rhel', 'fedora')):
                pm_supported = 'yum'
            elif ('zypper' in list_supported and
                  self.distro == 'SuSE'):
                pm_supported = 'zypper'
            else:
                pm_supported = list_supported[0]

        return pm_supported


class SoftwareManager:

    """
    Package management abstraction layer.

    It supports a set of common package operations for testing purposes, and it
    uses the concept of a backend, a helper class that implements the set of
    operations of a given package management tool.
    """

    def __init__(self):
        """
        Lazily instantiate the object
        """
        self.initialized = False
        self.backend = None
        self.lowlevel_base_command = None
        self.base_command = None
        self.pm_version = None

    def _init_on_demand(self):
        """
        Determines the best supported package management system for the given
        operating system running and initializes the appropriate backend.
        """
        if not self.initialized:
            inspector = SystemInspector()
            backend_type = inspector.get_package_management()
            backend_mapping = SUPPORTED_PACKAGE_MANAGERS

            if backend_type not in backend_mapping.keys():
                raise NotImplementedError('Unimplemented package management '
                                          'system: %s.' % backend_type)

            backend = backend_mapping[backend_type]
            self.backend = backend()
            self.initialized = True

    def __getattr__(self, name):
        self._init_on_demand()
        return self.backend.__getattribute__(name)


class BaseBackend:

    """
    This class implements all common methods among backends.
    """

    def install_what_provides(self, path):
        """
        Installs package that provides [path].

        :param path: Path to file.
        """
        provides = self.provides(path)
        if provides is not None:
            return self.install(provides)
        else:
            log.warning('No package seems to provide %s', path)
            return False


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
        inst_version = process.system_output(cmd, ignore_status=True)

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
        log.debug("Listing all system packages (may take a while)")

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

    def list_files(self, name):
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

    def rpm_install(self, file_path, no_dependencies=False, replace=False):
        """
        Install the rpm file [file_path] provided.

        :param str file_path: file path of the installed package
        :param bool no_dependencies: whether to add "nodeps" flag
        :param bool replace: whether to replace existing package
        :returns: whether file is installed properly
        :rtype: bool
        """
        if not os.path.isfile(file_path):
            log.warning('Please provide proper rpm path')
            return False

        nodeps = "--nodeps " if no_dependencies else ""
        update = "-U" if replace else "-i"
        cmd = "rpm %s %s%s" % (update, nodeps, file_path)

        try:
            process.system(cmd)
            return True
        except process.CmdError as details:
            log.error(details)
            return False

    def rpm_verify(self, package_name):
        """
        Verify an RPM package with an installed one.

        :param str package_name: name of the verified package
        :returns: whether the verification was successful
        :rtype: bool
        """
        logging.info("Verifying package information.")
        cmd = "rpm -V " + package_name
        result = process.run(cmd, ignore_status=True)

        # unstable approach but currently works
        #installed_pattern = r"\s" + package_name + r" is installed\s+"
        #match = re.search(installed_pattern, result)
        match = (result.exit_status == 0)
        if match:
            logging.info("Verification successful.")
            return True
        else:
            logging.info(result.stdout_text.rstrip())
            return False

    def rpm_erase(self, package_name):
        """
        Erase an RPM package.

        :param str package_name: name of the erased package
        :returns: whether file is erased properly
        :rtype: bool
        """
        logging.warning("Erasing rpm package %s", package_name)
        cmd = "rpm -e " + package_name
        result = process.run(cmd, ignore_status=True)
        if result.exit_status:
            return False
        return True

    def prepare_source(self, spec_file, dest_path=None):
        """
        Rpmbuild the spec path and return build dir

        :param spec_path: spec path to install
        :return path: build directory
        """

        build_option = "-bp"
        if dest_path is not None:
            build_option += " --define '_builddir %s'" % dest_path
        else:
            log.error("Please provide a valid path")
            return ""
        try:
            process.system("rpmbuild %s %s" % (build_option, spec_file))
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
        subpaths = os.listdir(rpm_dir)
        subpacks = []
        for subpath in subpaths:
            if subpath == "." or subpath == "..":
                continue
            new_filepath = rpm_dir + "/" + subpath
            logging.debug("Checking path for rpm %s", new_filepath)
            # if path is file validate name and inject
            if os.path.isfile(new_filepath) and re.search(r"\s*.rpm$", os.path.basename(new_filepath)):
                logging.info("Marking package %s for setup", new_filepath)
                subpacks.append(new_filepath)
            elif os.path.isdir(new_filepath):
                subpacks += self.find_rpm_packages(new_filepath)
        return subpacks

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
                verified = self.rpm_verify(package_name) if installed else False
                if installed and not verified:
                    self.rpm_erase(package_name)
                if not installed or not verified:
                    success = self.rpm_install(package_path, no_dependencies)
                    if not success:
                        failed_packages.append(package_path)
            if len(packages) == len(failed_packages) > 0:
                logging.warning("Some of the rpm packages could not be "
                                "installed: %s", ", ".join(failed_packages))
                return False
            packages = failed_packages
        return True


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

    def list_all(self):
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


class YumBackend(RpmBackend):

    """
    Implements the yum backend for software manager.

    Set of operations for the yum package manager, commonly found on Yellow Dog
    Linux and Red Hat based distributions, such as Fedora and Red Hat
    Enterprise Linux.
    """

    def __init__(self, cmd='yum'):
        """
        Initializes the base command and the yum package repository.
        """
        super(YumBackend, self).__init__()
        self.base_command = '%s -y ' % utils_path.find_command(cmd)
        self.repo_file_path = '/etc/yum.repos.d/avocado-managed.repo'
        self.cfgparser = configparser.ConfigParser()
        self.cfgparser.read(self.repo_file_path)
        version_result = process.run(self.base_command + '--version',
                                     verbose=False,
                                     ignore_status=True)
        version_first_line = version_result.stdout_text.splitlines()[0].strip()
        try:
            ver = re.findall(r'\d*.\d*.\d*', version_first_line)[0]
        except IndexError:
            ver = version_first_line
        self.pm_version = ver
        log.debug('%s version: %s', cmd, self.pm_version)

        if HAS_YUM_MODULE:
            self.yum_base = yum.YumBase()
        else:
            self.yum_base = None
            log.error("%s module for Python is required. "
                      "Using the basic support from rpm and %s commands", cmd,
                      cmd)

    def _cleanup(self):
        """
        Clean up the yum cache so new package information can be downloaded.
        """
        process.system("yum clean all", sudo=True)

    def install(self, name):
        """
        Installs package [name]. Handles local installs.
        """
        i_cmd = self.base_command + 'install' + ' ' + name

        try:
            process.system(i_cmd, sudo=True)
            return True
        except process.CmdError:
            return False

    def remove(self, name):
        """
        Removes package [name].

        :param name: Package name (eg. 'ipython').
        """
        r_cmd = self.base_command + 'erase' + ' ' + name
        try:
            process.system(r_cmd, sudo=True)
            return True
        except process.CmdError:
            return False

    def add_repo(self, url):
        """
        Adds package repository located on [url].

        :param url: Universal Resource Locator of the repository.
        """
        # Check if we URL is already set
        for section in self.cfgparser.sections():
            for option, value in self.cfgparser.items(section):
                if option == 'url' and value == url:
                    return True

        # Didn't find it, let's set it up
        while True:
            section_name = 'software_manager' + '_'
            section_name += data_factory.generate_random_string(4)
            if not self.cfgparser.has_section(section_name):
                break
        try:
            self.cfgparser.add_section(section_name)
            self.cfgparser.set(section_name, 'name',
                               'Avocado managed repository')
            self.cfgparser.set(section_name, 'url', url)
            self.cfgparser.set(section_name, 'enabled', '1')
            self.cfgparser.set(section_name, 'gpgcheck', '0')
            prefix = 'avocado_software_manager'
            with tempfile.NamedTemporaryFile("w", prefix=prefix) as tmp_file:
                self.cfgparser.write(tmp_file)
                tmp_file.flush()    # Sync the content
                process.system('cp %s %s'
                               % (tmp_file.name, self.repo_file_path),
                               sudo=True)
            return True
        except (OSError, process.CmdError) as details:
            log.error(details)
            return False

    def remove_repo(self, url):
        """
        Removes package repository located on [url].

        :param url: Universal Resource Locator of the repository.
        """
        try:
            prefix = 'avocado_software_manager'
            with tempfile.NamedTemporaryFile("w", prefix=prefix) as tmp_file:
                for section in self.cfgparser.sections():
                    for option, value in self.cfgparser.items(section):
                        if option == 'url' and value == url:
                            self.cfgparser.remove_section(section)
                self.cfgparser.write(tmp_file.file)
                tmp_file.flush()    # Sync the content
                process.system('cp %s %s'
                               % (tmp_file.name, self.repo_file_path),
                               sudo=True)
                return True
        except (OSError, process.CmdError) as details:
            log.error(details)
            return False

    def upgrade(self, name=None):
        """
        Upgrade all available packages.

        Optionally, upgrade individual packages.

        :param name: optional parameter wildcard spec to upgrade
        :type name: str
        """
        if not name:
            r_cmd = self.base_command + 'update'
        else:
            r_cmd = self.base_command + 'update' + ' ' + name

        try:
            process.system(r_cmd, sudo=True)
            return True
        except process.CmdError:
            return False

    def provides(self, name):
        """
        Returns a list of packages that provides a given capability.

        :param name: Capability name (eg, 'foo').
        """
        if self.yum_base is None:
            log.error("The method 'provides' is disabled, "
                      "yum module is required for this operation")
            return None
        try:
            #Python API need to be passed globs along with name for searching
            #all possible occurrences of pattern 'name'
            d_provides = self.yum_base.searchPackageProvides(args=['*/' + name])
        except Exception as exc:  # pylint: disable=W0703
            log.error("Error searching for package that "
                      "provides %s: %s", name, exc)
            d_provides = []

        provides_list = [key for key in d_provides]
        if provides_list:
            return str(provides_list[0])
        else:
            return None

    def build_dep(self, name):
        """
        Install build-dependencies for package [name]

        :param name: name of the package

        :return True: If build dependencies are installed properly
        """

        try:
            process.system('yum-builddep -y --tolerant %s' % name, sudo=True)
            return True
        except process.CmdError as details:
            log.error(details)
            return False

    def get_source(self, name, dest_path):
        """
        Downloads the source package and prepares it in the given dest_path
        to be ready to build.

        :param name: name of the package
        :param dest_path: destination_path

        :return final_dir: path of ready-to-build directory
        """
        path = tempfile.mkdtemp(prefix='avocado_software_manager')
        try:
            if dest_path is None:
                log.error("Please provide a valid path")
                return ""
            for pkg in ["rpm-build", "yum-utils"]:
                if not self.check_installed(pkg):
                    if not self.install(pkg):
                        log.error("SoftwareManager (YumBackend) can't get "
                                  "packageswith dependency resolution: Package"
                                  " '%s' could not be installed", pkg)
                        return ""
            try:
                process.run('yumdownloader --assumeyes --verbose --source %s '
                            '--destdir %s' % (name, path))
                src_rpms = [_ for _ in next(os.walk(path))[2]
                            if _.endswith(".src.rpm")]
                if len(src_rpms) != 1:
                    log.error("Failed to get downloaded src.rpm from %s:\n%s",
                              path, next(os.walk(path))[2])
                    return ""
                if self.rpm_install(os.path.join(path, src_rpms[-1])):
                    if self.build_dep(name):
                        spec_path = os.path.join(os.environ['HOME'],
                                                 "rpmbuild", "SPECS",
                                                 "%s.spec" % name)
                        return self.prepare_source(spec_path, dest_path)
                    else:
                        log.error("Installing build dependencies failed")
                        return ""
                else:
                    log.error("Installing source rpm failed")
                    return ""
            except process.CmdError as details:
                log.error(details)
                return ""
        finally:
            shutil.rmtree(path)


class DnfBackend(YumBackend):

    """
    Implements the dnf backend for software manager.

    DNF is the successor to yum in recent Fedora.
    """

    def __init__(self):
        """
        Initializes the base command and the DNF package repository.
        """
        super(DnfBackend, self).__init__(cmd='dnf')


class ZypperBackend(RpmBackend):

    """
    Implements the zypper backend for software manager.

    Set of operations for the zypper package manager, found on SUSE Linux.
    """

    def __init__(self):
        """
        Initializes the base command and the yum package repository.
        """
        super(ZypperBackend, self).__init__()
        self.base_command = utils_path.find_command('zypper') + ' -n'
        z_cmd = self.base_command + ' --version'
        cmd_result = process.run(z_cmd, ignore_status=True,
                                 verbose=False)
        out = cmd_result.stdout_text.strip()
        try:
            ver = re.findall(r'\d.\d*.\d*', out)[0]
        except IndexError:
            ver = out
        self.pm_version = ver
        log.debug('Zypper version: %s', self.pm_version)

    def install(self, name):
        """
        Installs package [name]. Handles local installs.

        :param name: Package Name.
        """
        i_cmd = self.base_command + ' install -l ' + name
        try:
            process.system(i_cmd, sudo=True)
            return True
        except process.CmdError:
            return False

    def add_repo(self, url):
        """
        Adds repository [url].

        :param url: URL for the package repository.
        """
        ar_cmd = self.base_command + ' addrepo ' + url
        try:
            process.system(ar_cmd, sudo=True)
            return True
        except process.CmdError:
            return False

    def remove_repo(self, url):
        """
        Removes repository [url].

        :param url: URL for the package repository.
        """
        rr_cmd = self.base_command + ' removerepo ' + url
        try:
            process.system(rr_cmd, sudo=True)
            return True
        except process.CmdError:
            return False

    def remove(self, name):
        """
        Removes package [name].
        """
        r_cmd = self.base_command + ' ' + 'erase' + ' ' + name

        try:
            process.system(r_cmd, sudo=True)
            return True
        except process.CmdError:
            return False

    def upgrade(self, name=None):
        """
        Upgrades all packages of the system.

        Optionally, upgrade individual packages.

        :param name: Optional parameter wildcard spec to upgrade
        :type name: str
        """
        if not name:
            u_cmd = self.base_command + ' update -l'
        else:
            u_cmd = self.base_command + ' ' + 'update' + ' ' + name

        try:
            process.system(u_cmd, sudo=True)
            return True
        except process.CmdError:
            return False

    def provides(self, name):
        """
        Searches for what provides a given file.

        :param name: File path.
        """
        p_cmd = self.base_command + ' what-provides ' + name
        list_provides = []
        try:
            p_output = process.system_output(p_cmd).split('\n')[4:]
            for line in p_output:
                line = [a.strip() for a in line.split('|')]
                try:
                    # state, pname, type, version, arch, repository = line
                    pname = line[1]
                    if pname not in list_provides:
                        list_provides.append(pname)
                except IndexError:
                    pass
            if len(list_provides) > 1:
                log.warning('More than one package found, '
                            'opting by the first queue result')
            if list_provides:
                log.info("Package %s provides %s", list_provides[0], name)
                return list_provides[0]
            return None
        except process.CmdError:
            return None

    def _source_install(self, name):
        """
        Source install the given package [name]
        Returns the SPEC file of the package

        :param name: name of the package

        :return path: path of the spec file
        """
        s_cmd = '%s source-install %s' % (self.base_command, name)

        try:
            process.system(s_cmd, sudo=True)
            s_cmd = '%s source-install -d %s' % (self.base_command, name)
            process.system(s_cmd, sudo=True)
            return '/usr/src/packages/SPECS/%s.spec' % name
        except process.CmdError:
            log.error('Installing source failed')
            return ""

    def get_source(self, name, dest_path):
        """
        Downloads the source package and prepares it in the given dest_path
        to be ready to build

        :param name: name of the package
        :param dest_path: destination_path

        :return final_dir: path of ready-to-build directory
        """
        if not self.check_installed("rpm-build"):
            if not self.install("rpm-build"):
                log.error("SoftwareManager (RpmBackend) can't get packages"
                          "with dependency resolution: Package 'rpm-build'"
                          "could not be installed")
                return ""
        try:
            spec_path = self._source_install(name)
            if spec_path:
                return self.prepare_source(spec_path, dest_path)
            else:
                log.error("Source not installed properly")
                return ""
        except process.CmdError as details:
            log.error(details)
            return ""


class AptBackend(DpkgBackend):

    """
    Implements the apt backend for software manager.

    Set of operations for the apt package manager, commonly found on Debian and
    Debian based distributions, such as Ubuntu Linux.
    """

    def __init__(self):
        """
        Initializes the base command and the debian package repository.
        """
        super(AptBackend, self).__init__()
        executable = utils_path.find_command('apt-get')
        self.base_command = executable + ' --yes --allow-unauthenticated'
        self.repo_file_path = '/etc/apt/sources.list.d/avocado.list'
        self.dpkg_force_confdef = ('-o Dpkg::Options::="--force-confdef" '
                                   '-o Dpkg::Options::="--force-confold"')
        cmd_result = process.run('apt-get -v | head -1',
                                 ignore_status=True,
                                 verbose=False,
                                 shell=True)
        out = cmd_result.stdout_text.strip()
        try:
            ver = re.findall(r'\d\S*', out)[0]
        except IndexError:
            ver = out
        self.pm_version = ver

        log.debug('apt-get version: %s', self.pm_version)
        # gdebi-core is necessary for local installation with dependency
        # handling
        if not self.check_installed('gdebi-core'):
            if not self.install('gdebi-core'):
                log.info("SoftwareManager (AptBackend) can't install packages "
                         "from local .deb files with dependency resolution: "
                         "Package 'gdebi-core' could not be installed")
        os.environ['DEBIAN_FRONTEND'] = 'noninteractive'

    def install(self, name):
        """
        Installs package [name].

        :param name: Package name.
        """
        if os.path.isfile(name):
            i_cmd = utils_path.find_command('gdebi') + ' -n -q ' + name
        else:
            command = 'install'
            i_cmd = " ".join([self.base_command, self.dpkg_force_confdef,
                              command, name])

        try:
            process.system(i_cmd, shell=True, sudo=True)
            return True
        except process.CmdError:
            return False

    def remove(self, name):
        """
        Remove package [name].

        :param name: Package name.
        """
        command = 'remove'
        flag = '--purge'
        r_cmd = self.base_command + ' ' + command + ' ' + flag + ' ' + name

        try:
            process.system(r_cmd, sudo=True)
            return True
        except process.CmdError:
            return False

    def add_repo(self, repo):
        """
        Add an apt repository.

        :param repo: Repository string. Example:
                'deb http://archive.ubuntu.com/ubuntu/ maverick universe'
        """
        def _add_repo_file():
            add_cmd = "bash -c \"echo '%s' > %s\"" % (repo, self.repo_file_path)
            process.system(add_cmd, shell=True, sudo=True)

        def _get_repo_file_contents():
            with open(self.repo_file_path, 'r') as repo_file:
                return repo_file.read()

        if not os.path.isfile(self.repo_file_path):
            _add_repo_file()
            return True

        repo_file_contents = _get_repo_file_contents()
        if repo not in repo_file_contents:
            try:
                _add_repo_file()
                return True
            except process.CmdError:
                return False

    def remove_repo(self, repo):
        """
        Remove an apt repository.

        :param repo: Repository string. Example:
                'deb http://archive.ubuntu.com/ubuntu/ maverick universe'
        """
        try:
            new_file_contents = []
            with open(self.repo_file_path, 'r') as repo_file:
                for line in repo_file.readlines():
                    if line != repo:
                        new_file_contents.append(line)
            new_file_contents = "\n".join(new_file_contents)
            prefix = "avocado_software_manager"
            with tempfile.NamedTemporaryFile("w", prefix=prefix) as tmp_file:
                tmp_file.write(new_file_contents)
                tmp_file.flush()    # Sync the content
                process.system('cp %s %s'
                               % (tmp_file.name, self.repo_file_path),
                               sudo=True)
        except (OSError, process.CmdError) as details:
            log.error(details)
            return False

    def upgrade(self, name=None):
        """
        Upgrade all packages of the system with eventual new versions.

        Optionally, upgrade individual packages.

        :param name: optional parameter wildcard spec to upgrade
        :type name: str
        """
        ud_command = 'update'
        ud_cmd = self.base_command + ' ' + ud_command
        try:
            process.system(ud_cmd, sudo=True)
        except process.CmdError:
            log.error("Apt package update failed")

        if name:
            up_command = 'install --only-upgrade'
            up_cmd = " ".join([self.base_command, self.dpkg_force_confdef,
                               up_command, name])
        else:
            up_command = 'upgrade'
            up_cmd = " ".join([self.base_command, self.dpkg_force_confdef,
                               up_command])

        try:
            process.system(up_cmd, shell=True, sudo=True)
            return True
        except process.CmdError:
            return False

    def provides(self, name):
        """
        Return a list of packages that provide [name of package/file].

        :param name: File name.
        """
        try:
            command = utils_path.find_command('apt-file')
        except utils_path.CmdNotFoundError:
            self.install('apt-file')
            command = utils_path.find_command('apt-file')
        try:
            process.run(command + ' update')
        except process.CmdError:
            log.error("Apt file cache update failed")
        fu_cmd = command + ' search ' + name
        try:
            paths = filter(None, os.environ['PATH'].split(':'))
            provides = filter(None, process.run(fu_cmd).stdout_text.split('\n'))
            list_provides = []
            for each_path in paths:
                for line in provides:
                    try:
                        line = line.split(':')
                        package = line[0].strip()
                        lpath = line[1].strip()
                        if lpath == os.path.join(each_path, name) and package not in list_provides:
                            list_provides.append(package)
                    except IndexError:
                        pass
            if len(list_provides) > 1:
                log.warning('More than one package found, '
                            'opting by the first result')
            if list_provides:
                log.info("Package %s provides %s", list_provides[0], name)
                return list_provides[0]
            return None
        except process.CmdError:
            return None

    def get_source(self, name, path):
        """
        Download source for provided package. Returns the path with source placed.

        :param name: parameter wildcard package to get the source for

        :return path: path of ready-to-build source
        """
        if not self.check_installed('dpkg-dev'):
            if not self.install('dpkg-dev'):
                log.info("SoftwareManager (AptBackend) can't install packages "
                         "from local .deb files with dependency resolution: "
                         "Package 'dpkg-dev' could not be installed")
        src_cmd = '%s source %s' % (self.base_command, name)
        try:
            if self.build_dep(name):
                if not os.path.exists(path):
                    os.makedirs(path)
                os.chdir(path)
                process.system_output(src_cmd)
                for subdir in os.listdir(path):
                    if subdir.startswith(name) and os.path.isdir(subdir):
                        return os.path.join(path, subdir)
        except process.CmdError as details:
            log.error("Apt package source failed %s", details)
            return ""

    def build_dep(self, name):
        """
        Installed build-dependencies of a given package [name].

        :param name: parameter package to install build-dependencies for.

        :return True: If packages are installed properly
        """
        if not self.check_installed('dpkg-dev'):
            if not self.install('dpkg-dev'):
                log.info("SoftwareManager (AptBackend) can't install packages "
                         "from local .deb files with dependency resolution: "
                         "Package 'dpkg-dev' could not be installed")

        src_cmd = '%s build-dep %s' % (self.base_command, name)
        try:
            process.system_output(src_cmd)
            return True
        except process.CmdError as details:
            log.error("Apt package build-dep failed %s", details)
            return False


#: Mapping of package manager name to implementation class.
SUPPORTED_PACKAGE_MANAGERS = {
        'apt-get': AptBackend,
        'yum': YumBackend,
        'dnf': DnfBackend,
        'zypper': ZypperBackend,
        }


def install_distro_packages(distro_pkg_map, interactive=False):
    """
    Installs packages for the currently running distribution

    This utility function checks if the currently running distro is a
    key in the distro_pkg_map dictionary, and if there is a list of packages
    set as its value.

    If these conditions match, the packages will be installed using the
    software manager interface, thus the native packaging system if the
    currently running distro.

    :type distro_pkg_map: dict
    :param distro_pkg_map: mapping of distro name, as returned by
        utils.get_os_vendor(), to a list of package names
    :return: True if any packages were actually installed, False otherwise
    """
    if not interactive:
        os.environ['DEBIAN_FRONTEND'] = 'noninteractive'

    result = False
    pkgs = []
    detected_distro = distro.detect()

    distro_specs = [spec for spec in distro_pkg_map if
                    isinstance(spec, distro.Spec)]

    for distro_spec in distro_specs:
        if distro_spec.name != detected_distro.name:
            continue

        if (distro_spec.arch is not None and
                distro_spec.arch != detected_distro.arch):
            continue

        if int(detected_distro.version) < distro_spec.min_version:
            continue

        if (distro_spec.min_release is not None and
                int(detected_distro.release) < distro_spec.min_release):
            continue

        pkgs = distro_pkg_map[distro_spec]
        break

    if not pkgs:
        log.info("No specific distro release package list")

        # when comparing distro names only, fallback to a lowercase version
        # of the distro name is it's more common than the case as detected
        pkgs = distro_pkg_map.get(detected_distro.name, None)
        if not pkgs:
            pkgs = distro_pkg_map.get(detected_distro.name.lower(), None)

        if not pkgs:
            log.error("No generic distro package list")

    if pkgs:
        needed_pkgs = []
        software_manager = SoftwareManager()
        for pkg in pkgs:
            if not software_manager.check_installed(pkg):
                needed_pkgs.append(pkg)
        if needed_pkgs:
            text = ' '.join(needed_pkgs)
            log.info('Installing packages "%s"', text)
            result = software_manager.install(text)
    else:
        log.error("No packages found for %s %s %s %s",
                  detected_distro.name, detected_distro.arch,
                  detected_distro.version, detected_distro.release)
    return result


def main():
    parser = argparse.ArgumentParser(
        "install|remove|check-installed|list-all|list-files|add-repo|"
        "remove-repo|upgrade|what-provides|install-what-provides arguments")
    parser.add_argument('--verbose', dest="debug", action='store_true',
                        help='include debug messages in console output')

    _, args = parser.parse_known_args()
    software_manager = SoftwareManager()
    if args:
        action = args[0]
        args = " ".join(args[1:])
    else:
        action = 'show-help'

    if action == 'install':
        if software_manager.install(args):
            log.info("Packages %s installed successfully", args)
        else:
            log.error("Failed to install %s", args)

    elif action == 'remove':
        if software_manager.remove(args):
            log.info("Packages %s removed successfully", args)
        else:
            log.error("Failed to remove %s", args)

    elif action == 'check-installed':
        if software_manager.check_installed(args):
            log.info("Package %s already installed", args)
        else:
            log.info("Package %s not installed", args)

    elif action == 'list-all':
        for pkg in software_manager.list_all():
            log.info(pkg)

    elif action == 'list-files':
        for f in software_manager.list_files(args):
            log.info(f)

    elif action == 'add-repo':
        if software_manager.add_repo(args):
            log.info("Repo %s added successfully", args)
        else:
            log.error("Failed to remove repo %s", args)

    elif action == 'remove-repo':
        if software_manager.remove_repo(args):
            log.info("Repo %s removed successfully", args)
        else:
            log.error("Failed to remove repo %s", args)

    elif action == 'upgrade':
        if software_manager.upgrade():
            log.info("Package manager upgrade successful")

    elif action == 'what-provides':
        provides = software_manager.provides(args)
        if provides is not None:
            log.info("Package %s provides %s", provides, args)

    elif action == 'install-what-provides':
        if software_manager.install_what_provides(args):
            log.info("Installed successfully what provides %s", args)

    elif action == 'show-help':
        parser.print_help()
