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
        initial_dirs = self.params.get('INITIAL_DIRS', default=10)
        runs = self.params.get('RUNS', default=30)

        args = []
        args.append('-D %s ' % self.srcdir)
        args.append('-s %s ' % self.srcdir)
        args.append('-i %d ' % initial_dirs)
        args.append('-r %d ' % runs)

        # Using python explicitly due to the compilebench current
        # shebang set to python2.4
        cmd = ('python %s/compilebench %s' % (self.srcdir, " ".join(args)))
        process.run(cmd)


if __name__ == "__main__":
    main()
