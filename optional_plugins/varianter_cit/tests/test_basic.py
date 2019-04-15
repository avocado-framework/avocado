import unittest
import os

from selftests import AVOCADO
from avocado.utils import process


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
basedir = os.path.abspath(basedir)


class Basic(unittest.TestCase):

    @staticmethod
    def test_interface():
        os.chdir(basedir)
        cmd_line = (
            '{0} variants --cit-order-of-combinations=2 '
            '--cit-parameter-file examples/varianter_cit/params.ini'
        ).format(AVOCADO)
        os.chdir(basedir)
        os.chdir(basedir)
        result = process.run(cmd_line)
        result.stdout.splitlines()
