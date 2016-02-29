#!/usr/bin/env python

import os

from avocado import Test
from avocado import main
from avocado.utils import archive
from avocado.utils import build
from avocado.utils import process
from avocado.utils import data_factory


class TrinityTest(Test):

    """
    Trinity syscall fuzzer wrapper.

    :see: http://codemonkey.org.uk/projects/trinity/
    :src: http://codemonkey.org.uk/projects/trinity/trinity-1.5.tar.xz (repackaged)

    :param tarball: Path to the trinity tarball relative to deps dir.
    :param stress: Name of the syscall you want to stress.
    :param victims_path: Path to victim files (must exist and have some bogus
                         files inside).
    """

    def setUp(self):
        """
        Build trinity.
        """
        tarball = self.params.get('tarball', default='trinity-1.5.tar.bz2')
        tarball_path = os.path.join(self.datadir, tarball)
        archive.extract(tarball_path, self.srcdir)
        self.srcdir = os.path.join(self.srcdir, 'trinity-1.5')
        os.chdir(self.srcdir)
        process.run('./configure.sh')
        build.make(self.srcdir)
        self.victims_path = data_factory.make_dir_and_populate(self.workdir)

    def test(self):
        """
        Execute the trinity syscall fuzzer with the appropriate params.
        """
        cmd = './trinity -m -I'
        process.run(cmd)
        cmd = './trinity -m'
        if self.params.get('stress'):
            cmd += " " + self.params.get('stress')
        if self.params.get('victims_path'):
            cmd += " -V " + self.params.get('victims_path')
        else:
            cmd += " -V " + self.victims_path
        process.run(cmd)


if __name__ == "__main__":
    main()
