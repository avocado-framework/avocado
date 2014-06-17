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
# Copyright: Red Hat Inc. 2014
# Author: Ruda Moura <rmoura@redhat.com>

from avocado import test
from avocado import job
from avocado.linux import kernel_build


class linuxbuild(test.Test):

    """
    Execute the Linux Build test.
    """
    default_params = {'linux_version': '3.14.5',
                      'linux_config': 'config'}

    def setup(self):
        kernel_version = self.params.linux_version
        config_path = tarball_path = self.get_deps_path('config')
        self.linux_build = kernel_build.KernelBuild(kernel_version,
                                                    config_path,
                                                    self.srcdir)
        self.linux_build.download()
        self.linux_build.uncompress()
        self.linux_build.configure()

    def action(self):
        self.linux_build.build()


if __name__ == "__main__":
    job.main()
