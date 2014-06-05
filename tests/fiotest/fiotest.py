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
#
# Based on Autotest fio test:
# https://github.com/autotest/autotest-client-tests/tree/master/fio

import os

from avocado import test
from avocado import job
from avocado.utils import archive
from avocado.utils import build
from avocado.utils import process


class fiotest(test.Test):

    """
    fio is an I/O tool meant to be used both for benchmark and
    stress/hardware verification.

    :see: http://freecode.com/projects/fio
    """

    default_params = {'fio_tarball': 'fio-2.1.7.tar.bz2',
                      'fio_job': 'fio-mixed.job'}

    def setup(self):
        """
        Build 'fio'.
        """
        self.cwd = os.getcwd()
        tarball_path = self.get_deps_path(self.params.fio_tarball)
        archive.extract(tarball_path, self.srcdir)
        fio_version = self.params.fio_tarball.split('.tar.')[0]
        self.srcdir = os.path.join(self.srcdir, fio_version)
        cmd = ('chmod +x %s' % os.path.join(self.srcdir, 'configure'))
        process.system(cmd)
        build.make(self.srcdir)

    def action(self):
        """
        Execute 'fio' with appropriate parameters.
        """
        os.chdir(self.srcdir)
        cmd = ('./fio %s' % self.get_deps_path(self.params.fio_job))
        process.system(cmd)
        os.chdir(self.cwd)


if __name__ == "__main__":
    job.main()
