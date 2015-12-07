#!/usr/bin/env python

import os

from avocado import Test
from avocado import main
from avocado.utils import archive
from avocado.utils import build
from avocado.utils import process


class FioTest(Test):

    """
    fio is an I/O tool meant to be used both for benchmark and
    stress/hardware verification.

    :see: http://freecode.com/projects/fio

    :param fio_tarbal: name of the tarbal of fio suite located in deps path
    :param fio_job: config defining set of executed tests located in deps path
    """

    def setUp(self):
        """
        Build 'fio'.
        """
        fio_tarball = self.params.get('fio_tarball',
                                      default='fio-2.1.10.tar.bz2')
        tarball_path = self.get_data_path(fio_tarball)
        archive.extract(tarball_path, self.srcdir)
        fio_version = fio_tarball.split('.tar.')[0]
        self.srcdir = os.path.join(self.srcdir, fio_version)
        build.make(self.srcdir)

    def test(self):
        """
        Execute 'fio' with appropriate parameters.
        """
        os.chdir(self.srcdir)
        fio_job = self.params.get('fio_job', default='fio-mixed.job')
        cmd = ('./fio %s' % self.get_data_path(fio_job))
        process.system(cmd)


if __name__ == "__main__":
    main()
