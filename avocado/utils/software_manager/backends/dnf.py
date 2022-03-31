import logging

from avocado.utils import process
from avocado.utils.software_manager.backends.yum import YumBackend

log = logging.getLogger('avocado.utils.software_manager')


class DnfBackend(YumBackend):

    """
    Implements the dnf backend for software manager.

    DNF is the successor to yum in recent Fedora.
    """

    def __init__(self):
        """
        Initializes the base command and the DNF package repository.
        """
        super().__init__(cmd='dnf')

    def build_dep(self, name):
        """
        Install build-dependencies for package [name]

        :param name: name of the package

        :return True: If build dependencies are installed properly
        """
        try:
            process.system(f'{self.base_command} builddep {name}',
                           sudo=True)
            return True
        except process.CmdError as details:
            log.error(details)
            return False
