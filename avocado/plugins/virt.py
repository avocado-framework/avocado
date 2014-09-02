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
# Copyright: Red Hat Inc. 2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Virtualization testing plugin.
"""

from avocado.plugins import plugin
from avocado.virt.qemu import path


class VirtOptions(plugin.Plugin):

    """
    Add virtualization testing related options.
    """

    name = 'virt'
    enabled = True

    def configure(self, parser):
        try:
            qemu_bin_default = path.get_qemu_binary()
        except:
            qemu_bin_default = 'qemu'

        try:
            qemu_dst_default = path.get_qemu_dst_binary()
        except:
            qemu_dst_default = 'qemu'

        self.parser = parser
        self.parser.runner.add_argument(
            '--qemu-bin', type=str,
            dest='qemu_bin',
            help=('Path to a custom qemu binary to be tested. Default path: %s'
                  % qemu_bin_default))
        self.parser.runner.add_argument(
            '--qemu-dst-bin', type=str,
            dest='qemu_dst_bin',
            help=('Path to a destination qemu binary to be tested. Used as '
                  'incoming qemu in migration tests. Default path: %s'
                  % qemu_dst_default))

        self.configured = True
