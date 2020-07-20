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


"""
Software package management library.

This is an abstraction layer on top of the existing distributions high level
package managers. It supports package operations useful for testing purposes,
and multiple high level package managers (here called backends).
"""

__all__ = ['install_distro_packages', 'SoftwareManager']


from .distro_packages import install_distro_packages
from .manager import SoftwareManager
