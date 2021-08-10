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

    def __init__(self, session=None):
        """
        Initializes the base command and the yum package repository.

        :param session: ssh connection that represents another machine
        :type session: avocado.utils.ssh.Session
        """
        super(ZypperBackend, self).__init__(session=session)
        self.base_command = utils_path.find_command('zypper', self.session) + ' -n'
        z_cmd = self.base_command + ' --version'
        if self.session:
            cmd_result = self.session.cmd(z_cmd, ignore_status=True)
        else:
            cmd_result = process.run(z_cmd, ignore_status=True, verbose=False)
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
            if self.session:
                self.session.cmd('sudo ' + i_cmd)
            else:
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
            if self.session:
                self.session.cmd('sudo ' + ar_cmd)
            else:
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
            if self.session:
                self.session.cmd('sudo ' + rr_cmd)
            else:
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
            if self.session:
                self.session.cmd('sudo ' + r_cmd)
            else:
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
            if self.session:
                self.session.cmd('sudo ' + u_cmd)
            else:
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
            if self.session:
                p_output = self.session.cmd(p_cmd).stdout_text.split('\n')[4:]
            else:
                p_output = process.system_output(p_cmd).decode('utf-8').split('\n')[4:]

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
            if self.session:
                self.session.cmd('sudo ' + s_cmd)
            else:
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
            if self.session:
                self.session.cmd('sudo ' + s_cmd)
            else:
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
                return self.prepare_source(spec_path, dest_path, session=self.session)
            else:
                log.error("Source not installed properly")
                return ""
        except process.CmdError as details:
            log.error(details)
            return ""
