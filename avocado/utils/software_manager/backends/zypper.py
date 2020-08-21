import logging
import re

from ... import path as utils_path
from ... import process
from .rpm import RpmBackend

log = logging.getLogger('avocado.utils.software_manager')


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

    def build_dep(self, name):
        """Return True if build-dependencies are installed for provided package

        Keyword argument:
        name -- name of the package
        """
        s_cmd = '%s source-install -d %s' % (self.base_command, name)

        try:
            process.system(s_cmd, sudo=True)
            return True
        except process.CmdError:
            log.error('Installing dependencies failed')
            return False

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
            if self.build_dep(name):
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
