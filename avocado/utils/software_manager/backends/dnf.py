import logging

from ... import process
from .yum import YumBackend

log = logging.getLogger('avocado.utils.software_manager')


class DnfBackend(YumBackend):

    """
    Implements the dnf backend for software manager.

    DNF is the successor to yum in recent Fedora.
    """

    def __init__(self, session=None):
        """
        Initializes the base command and the DNF package repository.

        :param session: ssh connection to manage the dnf package manager of
                        another machine
        :type session: avocado.utils.ssh.Session
        """
        super(DnfBackend, self).__init__(cmd='dnf', session=session)

    def build_dep(self, name):
        """
        Install build-dependencies for package [name]

        :param name: name of the package

        :return True: If build dependencies are installed properly
        """
        try:
            cmd = '%s builddep %s' % (self.base_command, name)
            if self.session:
                self.session.cmd("sudo %s" % cmd)
            else:
                process.system(cmd, sudo=True)
            return True
        except process.CmdError as details:
            log.error(details)
            return False
