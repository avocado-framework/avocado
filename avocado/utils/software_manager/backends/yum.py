import configparser
import logging
import os
import re
import shutil
import tempfile

from ... import data_factory
from ... import path as utils_path
from ... import process
from .rpm import RpmBackend

try:
    import yum
except ImportError:
    HAS_YUM_MODULE = False
else:
    HAS_YUM_MODULE = True


log = logging.getLogger('avocado.utils.software_manager')


class YumBackend(RpmBackend):

    """
    Implements the yum backend for software manager.

    Set of operations for the yum package manager, commonly found on Yellow Dog
    Linux and Red Hat based distributions, such as Fedora and Red Hat
    Enterprise Linux.
    """

    #: Path to the repository managed by Avocado
    REPO_FILE_PATH = '/etc/yum.repos.d/avocado-managed.repo'
    REMOTE_REPO_FILE_PATH = '/tmp/avocado-managed.repo'

    def __init__(self, cmd='yum', session=None):
        """
        Initializes the base command and the yum package repository.
        """
        super(YumBackend, self).__init__(session=session)
        self.cmd = cmd
        self.base_command = '%s -y ' % utils_path.find_command(cmd, session=self.session)
        self._cfgparser = None
        self._set_version(cmd)
        self._yum_base = None

    @property
    def repo_config_parser(self):
        if self._cfgparser is None:
            self._cfgparser = configparser.ConfigParser()
            if self.session:
                self._cfgparser.read(self.REMOTE_REPO_FILE_PATH)
            else:
                self._cfgparser.read(self.REPO_FILE_PATH)
        return self._cfgparser

    @property
    def yum_base(self):
        if self._yum_base is None:
            if HAS_YUM_MODULE and not self.session:
                self._yum_base = yum.YumBase()
            else:
                log.debug("%s module for Python is required to use the "
                          "'provides' command. Using the basic support "
                          "from rpm and %s commands", self.cmd, self.cmd)
        return self._yum_base

    @staticmethod
    def _cleanup(session=None):
        """
        Clean up the yum cache so new package information can be downloaded.

        :param session: ssh connection that represents another machine
        :type session: avocado.utils.ssh.Session
        """
        if session:
            session.cmd("sudo yum clean all")
        else:
            process.system("yum clean all", sudo=True)

    def _set_version(self, cmd):
        if self.session:
            result = self.session.cmd("%s --version" % self.base_command,
                                      ignore_status=True)
        else:
            result = process.run(self.base_command + '--version',
                                 verbose=False,
                                 ignore_status=True)
        first_line = result.stdout_text.splitlines()[0].strip()
        try:
            ver = re.findall(r'\d*.\d*.\d*', first_line)[0]
        except IndexError:
            ver = first_line
        self.pm_version = ver
        log.debug('%s version: %s', cmd, self.pm_version)

    def install(self, name):
        """
        Installs package [name]. Handles local installs.
        """
        i_cmd = self.base_command + 'install' + ' ' + name

        try:
            if self.session:
                self.session.cmd("sudo %s" % i_cmd)
            else:
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
            if self.session:
                self.session.cmd("sudo %s" % r_cmd)
            else:
                process.system(r_cmd, sudo=True)
            return True
        except process.CmdError:
            return False

    def add_repo(self, url):
        """
        Adds package repository located on [url].

        :param url: Universal Resource Locator of the repository.
        """
        if self.session:
            # Before we add the url to the config file, we sync it from remote machine
            if self.session.cmd("test -f %s" % self.REPO_FILE_PATH).exit_status != 0:
                self.session.cmd("touch %s" % self.REPO_FILE_PATH)
            self.session.copy_files(self.session.host + ":" + self.REPO_FILE_PATH,
                                    self.REMOTE_REPO_FILE_PATH)

        # Check if we URL is already set
        for section in self.repo_config_parser.sections():
            for option, value in self.repo_config_parser.items(section):
                if option == 'url' and value == url:
                    return True

        # Didn't find it, let's set it up
        while True:
            section_name = 'software_manager' + '_'
            section_name += data_factory.generate_random_string(4)
            if not self.repo_config_parser.has_section(section_name):
                break
        try:
            self.repo_config_parser.add_section(section_name)
            self.repo_config_parser.set(section_name, 'name',
                                        'Avocado managed repository')
            self.repo_config_parser.set(section_name, 'baseurl', url)
            self.repo_config_parser.set(section_name, 'enabled', '1')
            self.repo_config_parser.set(section_name, 'gpgcheck', '0')
            prefix = 'avocado_software_manager'
            with tempfile.NamedTemporaryFile("w+", prefix=prefix) as tmp_file:
                self.repo_config_parser.write(tmp_file)
                tmp_file.flush()
                # Sync the content
                if self.session:
                    self.session.copy_files(tmp_file.name,
                                            self.session.host + ":" + self.REPO_FILE_PATH)
                else:
                    process.system('cp %s %s'
                                   % (tmp_file.name, self.REPO_FILE_PATH),
                                   sudo=True)
            return True
        except (OSError, process.CmdError, configparser.Error) as details:
            log.error(details)
            return False

    def remove_repo(self, url):
        """
        Removes package repository located on [baseurl].

        :param url: Universal Resource Locator of the repository.
        """

        if self.session:
            # Before we remove the url to the config file, we sync it from remote machine
            if self.session.cmd("test -f %s" % self.REPO_FILE_PATH).exit_status != 0:
                return True  # nothing to remove
            self.session.copy_files(self.session.host + ":" + self.REPO_FILE_PATH,
                                    self.REMOTE_REPO_FILE_PATH)

        try:
            prefix = 'avocado_software_manager'
            with tempfile.NamedTemporaryFile("w+", prefix=prefix) as tmp_file:
                for section in self.repo_config_parser.sections():
                    for option, value in self.repo_config_parser.items(section):
                        if option == 'baseurl' and value == url:
                            self.repo_config_parser.remove_section(section)
                self.repo_config_parser.write(tmp_file.file)
                tmp_file.flush()    # Sync the content
                if self.session:
                    self.session.copy_files(tmp_file.name,
                                            self.session.host + ":" + self.REPO_FILE_PATH)
                else:
                    process.system('cp %s %s'
                                   % (tmp_file.name, self.REPO_FILE_PATH),
                                   sudo=True)
                return True
        except (OSError, process.CmdError, configparser.Error) as details:
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
            if self.session:
                self.session.cmd("sudo %s" % r_cmd)
            else:
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
                      "%s module is required for this operation", self.cmd)
            return None
        try:
            # Python API need to be passed globs along with name for searching
            # all possible occurrences of pattern 'name'
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

    @staticmethod
    def build_dep(name, session=None):
        """
        Install build-dependencies for package [name]

        :param name: name of the package
        :param session: ssh connection that represents another machine
        :type session: avocado.utils.ssh.Session

        :return True: If build dependencies are installed properly
        """
        cmd = 'yum-builddep -y --tolerant %s' % name
        try:
            if session:
                session.cmd("sudo %s" % cmd)
            else:
                process.system(cmd, sudo=True)
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
        if self.session:
            self.session.cmd("mkdir %s" % path)
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
                cmd = 'yumdownloader --assumeyes --verbose --source %s --destdir %s' % (name, path)
                if self.session:
                    self.session.cmd(cmd)
                    src_rpms = self.session.cmd("find %s -name \'*.src.rpm\'" % path).stdout_text.split('\n')
                    src_rpms = list(filter(None, src_rpms))  # remove empty items
                else:
                    process.run(cmd)
                    src_rpms = [_ for _ in next(os.walk(path))[2]
                                if _.endswith(".src.rpm")]
                if len(src_rpms) != 1:
                    if self.session:
                        log.error("Failed to get downloaded src.rpm from %s:%s:\n%s",
                                  self.session.host, path, src_rpms)
                    else:
                        log.error("Failed to get downloaded src.rpm from %s:\n%s",
                                  path, next(os.walk(path))[2])
                    return ""

                if self.rpm_install(os.path.join(path, src_rpms[-1]), session=self.session):
                    if self.session:
                        spec_path = os.path.join(self.session.cmd("echo $HOME").stdout_text.rstrip(),
                                                 "rpmbuild", "SPECS",
                                                 "%s.spec" % name)
                    else:
                        spec_path = os.path.join(os.environ['HOME'],
                                                 "rpmbuild", "SPECS",
                                                 "%s.spec" % name)
                    if self.build_dep(spec_path):
                        return self.prepare_source(spec_path, dest_path, session=self.session)
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
            if self.session:
                self.session.cmd("rm -r %s" % path)
            else:
                shutil.rmtree(path)
