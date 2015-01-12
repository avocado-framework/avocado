#!/usr/bin/python

import os

from avocado import test
from avocado import job
from avocado.utils import archive
from avocado.utils import build
from avocado.utils import process


class FioTest(test.Test):

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
        tarball_path = self.get_data_path(self.params.fio_tarball)
        archive.extract(tarball_path, self.srcdir)
        fio_version = self.params.fio_tarball.split('.tar.')[0]
        self.srcdir = os.path.join(self.srcdir, fio_version)
        build.make(self.srcdir)

    def action(self):
        """
        Execute 'fio' with appropriate parameters.
        """
        os.chdir(self.srcdir)
        cmd = ('./fio %s' % self.get_data_path(self.params.fio_job))
        process.system(cmd)


if __name__ == "__main__":
    job.main()
