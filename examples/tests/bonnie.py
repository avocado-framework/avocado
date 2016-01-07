#!/usr/bin/env python

import os

from avocado import Test
from avocado import main
from avocado.utils import archive
from avocado.utils import build
from avocado.utils import process


class Bonnie(Test):

    """
    Bonnie++ is a benchmark suite that is aimed at performing a number
    of simple tests of hard drive and file system performance.
    """

    def setUp(self):
        """
        Build bonnie++
        Source:
         http://www.coker.com.au/bonnie++/experimental/bonnie++-1.96.tgz
        """
        bonnie_tarball = self.params.get('bonnie_tarball',
                                         default='bonnie++-1.96.tgz')
        tarball_path = self.get_data_path(bonnie_tarball)
        archive.extract(tarball_path, self.srcdir)
        bonnie_version = bonnie_tarball.split('.tgz')[0]
        self.srcdir = os.path.join(self.srcdir, bonnie_version)
        os.chdir(self.srcdir)
        process.run('./configure')
        build.make(self.srcdir)

    def test(self):
        """
        Run 'bonnie' with its arguments
        """
        scratch_dir = self.params.get('scratch-dir', default=self.srcdir)
        uid_to_use = self.params.get('uid-to-use', default=None)
        number_to_stat = self.params.get('number-to-stat', default=2048)

        args = []
        args.append('-d %s' % scratch_dir)
        args.append('-n %s' % number_to_stat)
        if uid_to_use is not None:
            args.append('-u %s' % uid_to_use)

        cmd = ('%s/bonnie++ %s' % (self.srcdir, " ".join(args)))
        process.run(cmd)


if __name__ == "__main__":
    main()
