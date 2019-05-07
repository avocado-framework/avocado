import os
import shutil
import tempfile
import unittest

from avocado.utils import process

from selftests import AVOCADO, BASEDIR


class Variants(unittest.TestCase):

    def test_max_variants(self):
        os.chdir(BASEDIR)
        cmd_line = (
            '{0} variants --cit-order-of-combinations=5 '
            '--cit-parameter-file examples/varianter_cit/params.ini'
        ).format(AVOCADO)
        result = process.run(cmd_line)
        lines = result.stdout.splitlines()
        self.assertEqual(b'CIT Variants (216):', lines[0])
        self.assertEqual(217, len(lines))


class Run(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def test(self):
        os.chdir(BASEDIR)
        params_path = os.path.join(BASEDIR, 'examples',
                                   'varianter_cit', 'params.ini')
        test_path = os.path.join(BASEDIR, 'examples',
                                 'tests', 'cit_parameters.py')
        cmd_line = (
            '{0} --show=test run --sysinfo=off --job-results-dir={1} '
            '--cit-order-of-combinations=1 '
            '--cit-parameter-file={2} '
            '-- {3}'
        ).format(AVOCADO, self.tmpdir, params_path, test_path)
        result = process.run(cmd_line)
        # all values of colors should be looked for at least once
        self.assertIn(b"PARAMS (key=color, path=*, default=None) => 'black'",
                      result.stdout)
        self.assertIn(b"PARAMS (key=color, path=*, default=None) => 'gold'",
                      result.stdout)
        self.assertIn(b"PARAMS (key=color, path=*, default=None) => 'red'",
                      result.stdout)
        self.assertIn(b"PARAMS (key=color, path=*, default=None) => 'green'",
                      result.stdout)
        # all values of shape should be looked for at least once
        self.assertIn(b"PARAMS (key=shape, path=*, default=None) => 'square'",
                      result.stdout)
        self.assertIn(b"PARAMS (key=shape, path=*, default=None) => 'triangle'",
                      result.stdout)
        self.assertIn(b"PARAMS (key=shape, path=*, default=None) => 'circle'",
                      result.stdout)
        # all values of state should be looked for at least once
        self.assertIn(b"PARAMS (key=state, path=*, default=None) => 'liquid'",
                      result.stdout)
        self.assertIn(b"PARAMS (key=state, path=*, default=None) => 'solid'",
                      result.stdout)
        self.assertIn(b"PARAMS (key=state, path=*, default=None) => 'gas'",
                      result.stdout)
        # all values of material should be looked for at least once
        self.assertIn(b"PARAMS (key=material, path=*, default=None) => 'leather'",
                      result.stdout)
        self.assertIn(b"PARAMS (key=material, path=*, default=None) => 'plastic'",
                      result.stdout)
        self.assertIn(b"PARAMS (key=material, path=*, default=None) => 'aluminum'",
                      result.stdout)
        # all values of coating should be looked for at least once
        self.assertIn(b"PARAMS (key=coating, path=*, default=None) => 'anodic'",
                      result.stdout)
        self.assertIn(b"PARAMS (key=coating, path=*, default=None) => 'cathodic'",
                      result.stdout)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
