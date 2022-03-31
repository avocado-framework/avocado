import configparser
import logging
import os
import re
import shutil
import tempfile

from avocado.utils import data_factory
from avocado.utils import path as utils_path
from avocado.utils import process
from avocado.utils.software_manager.backends.rpm import RpmBackend

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

    def __init__(self, cmd='yum'):
        """
        Initializes the base command and the yum package repository.
        """
        super().__init__()
        self.cmd = cmd
        self.base_command = f'{utils_path.find_command(cmd)} -y '
        self._cfgparser = None
        self._set_version(cmd)
        self._yum_base = None

    @property
    def repo_config_parser(self):
        if self._cfgparser is None:
            self._cfgparser = configparser.ConfigParser()
            self._cfgparser.read(self.REPO_FILE_PATH)
        return self._cfgparser

    @property
    def yum_base(self):
        if self._yum_base is None:
            if HAS_YUM_MODULE:
                self._yum_base = yum.YumBase()
            else:
                log.debug("%s module for Python is required to use the "
                          "'provides' command. Using the basic support "
                          "from rpm and %s commands", self.cmd, self.cmd)
        return self._yum_base

    @staticmethod
    def _cleanup():
        """
        Clean up the yum cache so new package information can be downloaded.
        """
        process.system("yum clean all", sudo=True)

    def _set_version(self, cmd):
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
            self.repo_config_parser.set(section_name, 'url', url)
            self.repo_config_parser.set(section_name, 'enabled', '1')
            self.repo_config_parser.set(section_name, 'gpgcheck', '0')
            prefix = 'avocado_software_manager'
            with tempfile.NamedTemporaryFile("w", prefix=prefix) as tmp_file:
                self.repo_config_parser.write(tmp_file)
                tmp_file.flush()    # Sync the content
                process.system(f'cp {tmp_file.name} {self.REPO_FILE_PATH}',
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
                for section in self.repo_config_parser.sections():
                    for option, value in self.repo_config_parser.items(section):
                        if option == 'url' and value == url:
                            self.repo_config_parser.remove_section(section)
                self.repo_config_parser.write(tmp_file.file)
                tmp_file.flush()    # Sync the content
                process.system(f'cp {tmp_file.name} {self.REPO_FILE_PATH}',
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
    def build_dep(name):
        """
        Install build-dependencies for package [name]

        :param name: name of the package

        :return True: If build dependencies are installed properly
        """

        try:
            process.system(f'yum-builddep -y --tolerant {name}', sudo=True)
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
                process.run(f'yumdownloader --assumeyes --verbose '
                            f'--source {name} --destdir {path}')
                src_rpms = [_ for _ in next(os.walk(path))[2]
                            if _.endswith(".src.rpm")]
                if len(src_rpms) != 1:
                    log.error("Failed to get downloaded src.rpm from %s:\n%s",
                              path, next(os.walk(path))[2])
                    return ""
                if self.rpm_install(os.path.join(path, src_rpms[-1])):
                    spec_path = os.path.join(os.environ['HOME'],
                                             "rpmbuild", "SPECS",
                                             f"{name}.spec")
                    if self.build_dep(spec_path):
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
