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
# Copyright: RedHat 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>


import os

from avocado import test
from avocado import job
from avocado.utils import archive
from avocado.utils import build
from avocado.utils import process


class synctest(test.Test):

    """
    Execute the synctest test suite.
    """

    def setup(self, tarball='synctest.tar.bz2'):
        self.cwd = os.getcwd()
        tarball_path = self.get_deps_path(tarball)
        archive.extract(tarball_path, self.srcdir)
        self.srcdir = os.path.join(self.srcdir, 'synctest')
        build.make(self.srcdir)

    def action(self, length=100, loop=10):
        os.chdir(self.srcdir)
        cmd = './synctest %s %s' % (length, loop)
        process.system(cmd)
        os.chdir(self.cwd)


if __name__ == "__main__":
    job.main()
