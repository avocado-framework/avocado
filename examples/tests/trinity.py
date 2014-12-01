#!/usr/bin/python

import os

from avocado import test
from avocado import job
from avocado.utils import archive
from avocado.utils import build
from avocado.utils import process
from avocado.utils import data_factory


class trinity(test.Test):

    """
    Trinity syscall fuzzer wrapper.

    :see: http://codemonkey.org.uk/projects/trinity/
    :src: http://codemonkey.org.uk/projects/trinity/trinity-1.4.tar.xz (repackaged)

    :param tarball: Path to the trinity tarball relative to deps dir.
    :param stress: Name of the syscall you want to stress.
    :param victims_path: Path to victim files (must exist and have some bogus
                         files inside).
    """
    default_params = {'tarball': 'trinity-1.4.tar.bz2',
                      'victims_path': None,
                      'stress': None}

    def setup(self):
        """
        Build trinity.
        """
        tarball_path = self.get_data_path(self.params.tarball)
        archive.extract(tarball_path, self.srcdir)
        self.srcdir = os.path.join(self.srcdir, 'trinity-1.4')
        os.chdir(self.srcdir)
        process.run('./configure.sh')
        build.make(self.srcdir)
        self.victims_path = data_factory.make_dir_and_populate(self.workdir)

    def action(self):
        """
        Execute the trinity syscall fuzzer with the appropriate params.
        """
        cmd = './trinity -I'
        process.run(cmd)
        cmd = './trinity'
        if self.params.stress:
            cmd += " " + self.params.stress
        if self.params.victims_path:
            cmd += " -V " + self.params.victims_path
        else:
            cmd += " -V " + self.victims_path
        process.run(cmd)


if __name__ == "__main__":
    job.main()
