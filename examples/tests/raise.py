#!/usr/bin/python

import os
import shutil

import avocado

from avocado.utils import build
from avocado.utils import process


class Raise(avocado.Test):

    """
    A test that calls raise() to signals to itself.
    """

    default_params = {'source': 'raise.c',
                      'signal_number': 15}

    def setup(self):
        """
        Build 'raise'.
        """
        c_file = self.get_data_path(self.params.source)
        c_file_name = os.path.basename(c_file)
        dest_c_file = os.path.join(self.srcdir, c_file_name)
        shutil.copy(c_file, dest_c_file)
        build.make(self.srcdir,
                   env={'CFLAGS': '-g -O0'},
                   extra_args='raise')

    def action(self):
        """
        Execute 'raise'.
        """
        cmd = os.path.join(self.srcdir, 'raise %d' % self.params.signal_number)
        cmd_result = process.run(cmd, ignore_status=True)
        self.log.info(cmd_result)
        signum = self.params.signal_number
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
    avocado.main()
