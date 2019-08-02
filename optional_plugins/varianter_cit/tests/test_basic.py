import os
import tempfile
import unittest

from avocado.utils import process

from selftests import AVOCADO, BASEDIR, temp_dir_prefix


class Basic(unittest.TestCase):

    def test_max_variants(self):
        os.chdir(BASEDIR)
        params_path = os.path.join(BASEDIR, 'examples',
                                   'varianter_cit', 'test_params.cit')
        cmd_line = (
            '{0} variants --cit-order-of-combinations=2 '
            '--cit-parameter-file {1}'
        ).format(AVOCADO, params_path)
        result = process.run(cmd_line)
        lines = result.stdout.splitlines()
        self.assertEqual(b'CIT Variants (9):', lines[0])
        self.assertEqual(10, len(lines))
        for i in range(1, len(lines)):
            with self.subTest(combination=lines[i]):
                self.assertIn(b"green", lines[i])


class Run(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    def test(self):
        os.chdir(BASEDIR)
        params_path = os.path.join(BASEDIR, 'examples',
                                   'varianter_cit', 'test_params.cit')
        test_path = os.path.join(BASEDIR, 'examples',
                                 'tests', 'cit_parameters.py')
        cmd_line = (
            '{0} --show=test run --sysinfo=off --job-results-dir={1} '
            '--cit-order-of-combinations=1 '
            '--cit-parameter-file={2} '
            '-- {3}'
        ).format(AVOCADO, self.tmpdir.name, params_path, test_path)
        result = process.run(cmd_line)
        # all values should be looked for at least once
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
        self.tmpdir.cleanup()


if __name__ == '__main__':
    unittest.main()
