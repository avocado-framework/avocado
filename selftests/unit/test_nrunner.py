import sys
import unittest.mock

from avocado.core import nrunner


class Runnable(unittest.TestCase):

    def test_runnable_args(self):
        runnable = nrunner.Runnable('noop', 'uri', 'arg1', 'arg2')
        self.assertIn('arg1', runnable.args)
        self.assertIn('arg2', runnable.args)

    def test_runnable_kwargs(self):
        runnable = nrunner.Runnable('noop', 'uri',
                                    tags={'arch': set(['x86_64', 'ppc64'])})
        self.assertIn('x86_64', runnable.kwargs.get('tags').get('arch'))
        self.assertIn('ppc64', runnable.kwargs.get('tags').get('arch'))

    def test_runnable_args_kwargs(self):
        runnable = nrunner.Runnable('noop', 'uri', 'arg1', 'arg2',
                                    tags={'arch': set(['x86_64', 'ppc64'])})
        self.assertIn('arg1', runnable.args)
        self.assertIn('arg2', runnable.args)
        self.assertIn('x86_64', runnable.kwargs.get('tags').get('arch'))
        self.assertIn('ppc64', runnable.kwargs.get('tags').get('arch'))

    def test_kind_required(self):
        self.assertRaises(TypeError, nrunner.Runnable)

    def test_kind_noop(self):
        runnable = nrunner.Runnable('noop')
        self.assertEqual(runnable.kind, 'noop')

    def test_recipe_noop(self):
        open_mocked = unittest.mock.mock_open(read_data='{"kind": "noop"}')
        with unittest.mock.patch("builtins.open", open_mocked):
            runnable = nrunner.runnable_from_recipe("fake_path")
        self.assertEqual(runnable.kind, "noop")

    def test_recipe_exec(self):
        open_mocked = unittest.mock.mock_open(
            read_data='{"kind": "exec", "uri": "/bin/sh"}')
        with unittest.mock.patch("builtins.open", open_mocked):
            runnable = nrunner.runnable_from_recipe("fake_path")
        self.assertEqual(runnable.kind, "exec")
        self.assertEqual(runnable.uri, "/bin/sh")


class Runner(unittest.TestCase):

    def test_runner_noop(self):
        runnable = nrunner.Runnable('noop')
        runner = nrunner.runner_from_runnable(runnable)
        results = [status for status in runner.run()]
        self.assertEqual(results, [{'status': 'finished'}])

    def test_runner_exec(self):
        runnable = nrunner.Runnable('exec', sys.executable,
                                    '-c', '"import time; time.sleep(0.01)"')
        runner = nrunner.runner_from_runnable(runnable)
        results = [status for status in runner.run()]
        self.assertEqual(results[-1], {'status': 'finished',
                                       'returncode': 0,
                                       'stdout': b'',
                                       'stderr': b''})

    def test_runner_exec_test(self):
        runnable = nrunner.Runnable('exec-test', sys.executable,
                                    '-c', '"import time; time.sleep(0.01)"')
        runner = nrunner.runner_from_runnable(runnable)
        results = [status for status in runner.run()]
        self.assertEqual(results[-1], {'status': 'pass',
                                       'returncode': 0,
                                       'stdout': b'',
                                       'stderr': b''})

    def test_runner_python_unittest(self):
        runnable = nrunner.Runnable('python-unittest', 'unittest.TestCase')
        runner = nrunner.runner_from_runnable(runnable)
        results = [status for status in runner.run()]
        output1 = ('----------------------------------------------------------'
                   '------------\nRan 0 tests in ')
        output2 = 's\n\nOK\n'
        result = results[-1]
        self.assertEqual(result['status'], 'pass')
        self.assertTrue(result['output'].startswith(output1))
        self.assertTrue(result['output'].endswith(output2))


if __name__ == '__main__':
    unittest.main()
