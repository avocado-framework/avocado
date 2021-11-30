import logging
import os
import re
import tempfile

from avocado.utils import path as utils_path
from avocado.utils import process
from avocado.utils.software_manager.backends.dpkg import DpkgBackend

log = logging.getLogger('avocado.utils.software_manager')


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
            paths = list(filter(None, os.environ['PATH'].split(':')))
            provides = list(filter(None, process.run(fu_cmd).stdout_text.split('\n')))
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
