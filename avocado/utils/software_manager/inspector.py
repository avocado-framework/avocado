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


from .. import distro
from .. import path as utils_path
from .backends.apt import AptBackend
from .backends.dnf import DnfBackend
from .backends.yum import YumBackend
from .backends.zypper import ZypperBackend

#: Mapping of package manager name to implementation class.
SUPPORTED_PACKAGE_MANAGERS = {
        'apt-get': AptBackend,
        'yum': YumBackend,
        'dnf': DnfBackend,
        'zypper': ZypperBackend,
        }


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
