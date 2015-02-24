#!/usr/bin/python

import os

from avocado import test
from avocado import job
from avocado.utils import build
from avocado.utils import process


class Raise(test.Test):

    """
    A test that calls raise() to signals to itself.
    """

    default_params = {'source': 'raise.c',
                      'signal_number': 15}

    def setup(self):
        """
        Build 'raise'.
        """
        self.cwd = os.getcwd()
        c_file = self.get_data_path(self.params.source)
        self.srcdir = os.path.dirname(c_file)
        build.make(self.srcdir, extra_args='raise')

    def action(self):
        """
        Execute 'raise'.
        """
        cmd = os.path.join(self.srcdir, 'raise %d' % self.params.signal_number)
        cmd_result = process.run(cmd)
        self.log.info(cmd_result)

    def cleanup(self):
        """
        Clean up 'raise'.
        """
        os.unlink(os.path.join(self.srcdir, 'raise'))


if __name__ == "__main__":
    job.main()
