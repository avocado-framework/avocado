#!/usr/bin/env python

import os

from avocado import Test
from avocado import main
from avocado.utils import archive
from avocado.utils import process


class Compilebench(Test):

    """
    Compilebench tries to age a filesystem by simulating some of the
    disk IO common in creating, compiling, patching, stating and
    reading kernel trees.
    """

    def setUp(self):
        """
        Extract compilebench
        Source:
         https://oss.oracle.com/~mason/compilebench/compilebench-0.6.tar.bz2
        """
        cb_tarball = self.params.get('cb_tarball',
                                     default='compilebench-0.6.tar.bz2')
        tarball_path = self.get_data_path(cb_tarball)
        archive.extract(tarball_path, self.srcdir)
        cb_version = cb_tarball.split('.tar.')[0]
        self.srcdir = os.path.join(self.srcdir, cb_version)

    def test(self):
        """
        Run 'compilebench' with its arguments
        """
        num_kernel_trees = self.params.get('num_kernel_trees', default=10)
        num_random_runs = self.params.get('num_random_runs', default=30)

        args = []
        args.append('-D %s ' % self.srcdir)
        args.append('-s %s ' % self.srcdir)
        args.append('-i %d ' % num_kernel_trees)
        args.append('-r %d ' % num_random_runs)

        cmd = ('/usr/bin/env python %s/compilebench %s' % (self.srcdir,
                                                           " ".join(args)))

        process.run(cmd)


if __name__ == "__main__":
    main()
