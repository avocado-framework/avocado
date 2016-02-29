#!/usr/bin/env python

import os
import shutil

from avocado import Test
from avocado import main
from avocado.utils import build
from avocado.utils import process


class Raise(Test):

    """
    A test that calls raise() to signals to itself.

    :param source: name of the source file located in data path
    :param signal_number: Which signal number should be raised
    """

    def setUp(self):
        """
        Build 'raise'.
        """
        source = self.params.get('source', default='raise.c')
        c_file = os.path.join(self.datadir, source)
        c_file_name = os.path.basename(c_file)
        dest_c_file = os.path.join(self.srcdir, c_file_name)
        shutil.copy(c_file, dest_c_file)
        build.make(self.srcdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args='raise')

    def test(self):
        """
        Execute 'raise'.
        """
        signum = self.params.get('signal_number', default=15)
        cmd = os.path.join(self.srcdir, 'raise %d' % signum)
        cmd_result = process.run(cmd, ignore_status=True)
        self.log.info(cmd_result)
        if signum == 0:
            expected_result = 0
            self.assertIn("I'm alive!", cmd_result.stdout)
        elif 0 < signum < 65:
            expected_result = -signum
        else:
            expected_result = 255
            self.assertIn("raise: Invalid argument", cmd_result.stderr)
        self.assertEqual(cmd_result.exit_status, expected_result)


if __name__ == "__main__":
    main()
