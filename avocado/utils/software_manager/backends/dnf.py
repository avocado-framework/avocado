import logging

from ... import process
from .yum import YumBackend

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
        super(DnfBackend, self).__init__(cmd='dnf')

    def build_dep(self, name):
        """
        Install build-dependencies for package [name]

        :param name: name of the package

        :return True: If build dependencies are installed properly
        """
        try:
            process.system('%s builddep %s' % (self.base_command, name),
                           sudo=True)
            return True
        except process.CmdError as details:
            log.error(details)
            return False
