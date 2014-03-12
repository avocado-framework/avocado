import os

from avocado import test
from avocado.utils import archive
from avocado.utils import build
from avocado.utils import process


class synctest(test.Test):

    """
    Execute the synctest test suite.
    """

    def setup(self, tarball='synctest.tar.bz2'):
        tarball_path = self.get_deps_path(tarball)
        archive.extract(tarball_path, self.srcdir)
        self.srcdir = os.path.join(self.srcdir, 'synctest')
        build.make(self.srcdir)

    def action(self, length=100, loop=10):
        os.chdir(self.srcdir)
        cmd = './synctest %s %s' % (length, loop)
        process.system(cmd)
