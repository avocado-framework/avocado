import os
import unittest

from avocado.utils import process


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
basedir = os.path.abspath(basedir)

AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD", "./scripts/avocado")


class Variants(unittest.TestCase):

    def test_max_variants(self):
        os.chdir(basedir)
        cmd_line = (
            '{0} variants --cit-order-of-combinations=5 '
            '--cit-parameter-file examples/varianter_cit/params.ini'
        ).format(AVOCADO)
        os.chdir(basedir)
        result = process.run(cmd_line)
        lines = result.stdout.splitlines()
        self.assertEqual(b'CIT Variants (216):', lines[0])
        self.assertEqual(217, len(lines))


if __name__ == '__main__':
    unittest.main()
