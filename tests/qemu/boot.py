#!/usr/bin/python

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
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

from avocado import job
from avocado.core import data_dir
from avocado.virt import test
from avocado.virt.qemu import machine


class boot(test.VirtTest):

    def setup(self):
        self.vm = machine.VM(self.params)
        self.vm.devices.add_display('none')
        self.vm.devices.add_vga('none')
        drive_file = data_dir.get_datafile_path('images', 'jeos-20-64.qcow2')
        self.vm.devices.add_drive(drive_file)
        self.vm.devices.add_net()

    def action(self):
        self.vm.launch()
        self.vm.setup_remote_login()

    def cleanup(self):
        self.vm.remote.run('shutdown -h now')
        self.vm.shutdown()


if __name__ == "__main__":
    job.main()
