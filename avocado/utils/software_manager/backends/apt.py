import logging
import os
import re
import tempfile

from ... import path as utils_path
from ... import process
from .dpkg import DpkgBackend

log = logging.getLogger('avocado.utils.software_manager')


class AptBackend(DpkgBackend):

    """
    Implements the apt backend for software manager.

    Set of operations for the apt package manager, commonly found on Debian and
    Debian based distributions, such as Ubuntu Linux.
    """

    def __init__(self, session=None):
        """
        Initializes the base command and the debian package repository.

        :param session: ssh connection to manage the apt package manager of
                        another machine
        :type session: avocado.utils.ssh.Session
        """
        super(AptBackend, self).__init__(session=session)
        executable = utils_path.find_command('apt-get', session=self.session)
        self.base_command = executable + ' --yes --allow-unauthenticated'
        self.repo_file_path = '/etc/apt/sources.list.d/avocado.list'
        self.dpkg_force_confdef = ('-o Dpkg::Options::="--force-confdef" '
                                   '-o Dpkg::Options::="--force-confold"')
        if self.session:
            cmd_result = self.session.cmd('apt-get -v | head -1',
                                          ignore_status=True)
        else:
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
        if self.session:
            if self.session.cmd('test -f %s' % name).exit_status == 0:
                i_cmd = utils_path.find_command('gdebi', self.session) + ' -n -q ' + name
        elif os.path.isfile(name):
            i_cmd = utils_path.find_command('gdebi') + ' -n -q ' + name
        else:
            command = 'install'
            i_cmd = " ".join([self.base_command, self.dpkg_force_confdef,
                              command, name])

        try:
            if self.session:
                self.session.cmd('sudo ' + i_cmd)
            else:
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
            if self.session:
                self.session.cmd('sudo ' + r_cmd)
            else:
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
            if self.session:
                self.session.cmd('sudo ' + add_cmd)
            else:
                process.system(add_cmd, shell=True, sudo=True)

        def _get_repo_file_contents():
            if self.session:
                return self.session.cmd('cat %s' % self.repo_file_path).stdout_text.split('/n')
            else:
                try:
                    return open(self.repo_file_path, 'r').read()
                except IOError as err:
                    log.debug('Could not open %s', self.repo_file_path)
                    log.debug('Exception: %s', str(err))
                    return None

        if self.session:
            if not self.session.cmd('test -f %s' % self.repo_file_path).exit_status == 0:
                _add_repo_file()
                return True
        elif not self.session and not os.path.isfile(self.repo_file_path):
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
            if self.session:
                repo_file = self.session.cmd('cat %s' % self.repo_file_path).stdout_text.split('/n')
            else:
                repo_file = open(self.repo_file_path, 'r').read()
            for line in repo_file:
                if line != repo:
                    new_file_contents.append(line)
            new_file_contents = "\n".join(new_file_contents)
            prefix = "avocado_software_manager"
            with tempfile.NamedTemporaryFile("w", prefix=prefix) as tmp_file:
                tmp_file.write(new_file_contents)
                tmp_file.flush()    # Sync the content
                if self.session:
                    self.session.copy_files(tmp_file.name, self.repo_file_path)
                else:
                    process.system('cp %s %s'
                                   % (tmp_file.name, self.repo_file_path),
                                   sudo=True)
        except (OSError, process.CmdError, IOError) as details:
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
            if self.session:
                self.session.cmd('sudo ' + ud_cmd)
            else:
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
            if self.session:
                self.session.cmd('sudo ' + up_cmd)
            else:
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
            command = utils_path.find_command('apt-file', session=self.session)
        except utils_path.CmdNotFoundError:
            self.install('apt-file')
            command = utils_path.find_command('apt-file', session=self.session)
        try:
            if self.session:
                self.session.cmd(command + ' update')
            else:
                process.run(command + ' update')
        except process.CmdError:
            log.error("Apt file cache update failed")
        fu_cmd = command + ' search ' + name
        try:
            if self.session:
                paths = list(filter(None, self.session.cmd('echo $PATH').stdout_text.split(':')))
                provides = list(filter(None, self.session.cmd(fu_cmd).stdout_text.split('/n')))
            else:
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
                if self.session:
                    if not self.session.cmd('[ -d %s ]' % path).exit_status == 0:
                        self.session.cmd('mkdir -p %s' % path)
                    self.session.cmd('cd %s' % path)
                    self.session.cmd(src_cmd)
                    for subdir in self.session.cmd('ls').stdout_text.split():
                        if subdir.startswith(name) and self.session.cmd('[ -d %s ]' % subdir).exit_status == 0:
                            return os.path.join(path, subdir)
                else:
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
            if self.session:
                self.session.cmd(src_cmd)
            else:
                process.system_output(src_cmd)
            return True
        except process.CmdError as details:
            log.error("Apt package build-dep failed %s", details)
            return False
