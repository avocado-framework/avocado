import os
import sys
import tempfile
import unittest.mock

from avocado.core import nrunner

from .. import temp_dir_prefix


class Runnable(unittest.TestCase):

    def test_runnable_args(self):
        runnable = nrunner.Runnable('noop', 'uri', 'arg1', 'arg2')
        self.assertIn('arg1', runnable.args)
        self.assertIn('arg2', runnable.args)

    def test_runnable_kwargs(self):
        runnable = nrunner.Runnable('noop', 'uri', key1='val1', key2='val2')
        self.assertEqual(runnable.kwargs.get('key1'), 'val1')
        self.assertEqual(runnable.kwargs.get('key2'), 'val2')

    def test_runnable_args_kwargs(self):
        runnable = nrunner.Runnable('noop', 'uri', 'arg1', 'arg2',
                                    key1='val1', key2='val2')
        self.assertIn('arg1', runnable.args)
        self.assertIn('arg2', runnable.args)
        self.assertEqual(runnable.kwargs.get('key1'), 'val1')
        self.assertEqual(runnable.kwargs.get('key2'), 'val2')

    def test_runnable_tags(self):
        runnable = nrunner.Runnable('noop', 'uri',
                                    tags={'arch': set(['x86_64', 'ppc64'])})
        self.assertIn('x86_64', runnable.tags.get('arch'))
        self.assertIn('ppc64', runnable.tags.get('arch'))

    def test_runnable_args_kwargs_tags(self):
        runnable = nrunner.Runnable('noop', 'uri', 'arg1', 'arg2',
                                    tags={'arch': set(['x86_64', 'ppc64'])},
                                    non_standard_option='non_standard_value')
        self.assertIn('arg1', runnable.args)
        self.assertIn('arg2', runnable.args)
        self.assertIn('x86_64', runnable.tags.get('arch'))
        self.assertIn('ppc64', runnable.tags.get('arch'))
        self.assertEqual(runnable.kwargs.get('non_standard_option'),
                         'non_standard_value')

    def test_kind_required(self):
        self.assertRaises(TypeError, nrunner.Runnable)

    def test_kind_noop(self):
        runnable = nrunner.Runnable('noop', None)
        self.assertEqual(runnable.kind, 'noop')

    def test_recipe_noop(self):
        open_mocked = unittest.mock.mock_open(read_data='{"kind": "noop"}')
        with unittest.mock.patch("builtins.open", open_mocked):
            runnable = nrunner.runnable_from_recipe("fake_path")
        self.assertEqual(runnable.kind, "noop")

    def test_recipe_exec(self):
        open_mocked = unittest.mock.mock_open(
            read_data=('{"kind": "exec", "uri": "/bin/sh", '
                       '"args": ["/etc/profile"], '
                       '"kwargs": {"TERM": "vt3270"}}'))
        with unittest.mock.patch("builtins.open", open_mocked):
            runnable = nrunner.runnable_from_recipe("fake_path")
        self.assertEqual(runnable.kind, "exec")
        self.assertEqual(runnable.uri, "/bin/sh")
        self.assertEqual(runnable.args, ("/etc/profile",))
        self.assertEqual(runnable.kwargs, {"TERM": "vt3270"})

    def test_runnable_command_args(self):
        runnable = nrunner.Runnable('noop', 'uri', 'arg1', 'arg2')
        actual_args = runnable.get_command_args()
        exp_args = ['-k', 'noop', '-u', 'uri', '-a', 'arg1', '-a', 'arg2']
        self.assertEqual(actual_args, exp_args)

    def test_get_dict(self):
        runnable = nrunner.Runnable('noop', '_uri_', 'arg1', 'arg2')
        self.assertEqual(runnable.get_dict(),
                         {'kind': 'noop', 'uri': '_uri_',
                          'args': ('arg1', 'arg2')})

    def test_get_json(self):
        runnable = nrunner.Runnable('noop', '_uri_', 'arg1', 'arg2')
        expected = '{"kind": "noop", "uri": "_uri_", "args": ["arg1", "arg2"]}'
        self.assertEqual(runnable.get_json(), expected)


class RunnableFromCommandLineArgs(unittest.TestCase):

    def test_noop(self):
        parsed_args = {'kind': 'noop', 'uri': None}
        runnable = nrunner.runnable_from_args(parsed_args)
        self.assertEqual(runnable.kind, 'noop')
        self.assertIsNone(runnable.uri)

    def test_exec_args(self):
        parsed_args = {'kind': 'exec', 'uri': '/path/to/executable',
                       'arg': ['-a', '-b', '-c']}
        runnable = nrunner.runnable_from_args(parsed_args)
        self.assertEqual(runnable.kind, 'exec')
        self.assertEqual(runnable.uri, '/path/to/executable')
        self.assertEqual(runnable.args, ('-a', '-b', '-c'))
        self.assertEqual(runnable.kwargs, {})

    def test_exec_args_kwargs(self):
        parsed_args = {'kind': 'exec', 'uri': '/path/to/executable',
                       'arg': ['-a', '-b', '-c'],
                       'kwargs': [('DEBUG', '1'), ('LC_ALL', 'C')]}
        runnable = nrunner.runnable_from_args(parsed_args)
        self.assertEqual(runnable.kind, 'exec')
        self.assertEqual(runnable.uri, '/path/to/executable')
        self.assertEqual(runnable.args, ('-a', '-b', '-c'))
        self.assertEqual(runnable.kwargs.get('DEBUG'), '1')
        self.assertEqual(runnable.kwargs.get('LC_ALL'), 'C')

    def test_kwargs_json_empty_dict(self):
        parsed_args = {'kind': 'noop', 'uri': None,
                       'kwargs': [('empty', 'json:{}')]}
        runnable = nrunner.runnable_from_args(parsed_args)
        self.assertEqual(runnable.kind, 'noop')
        self.assertIsNone(runnable.uri)
        self.assertEqual(runnable.kwargs.get('empty'), {})

    def test_kwargs_json_dict(self):
        parsed_args = {
            'kind': 'noop', 'uri': None,
            'kwargs': [('tags', 'json:{"arch": ["x86_64", "ppc64"]}'),
                       ('hi', 'json:"hello"')]
        }
        runnable = nrunner.runnable_from_args(parsed_args)
        self.assertEqual(runnable.kind, 'noop')
        self.assertIsNone(runnable.uri)
        self.assertEqual(runnable.kwargs.get('hi'), 'hello')
        self.assertEqual(runnable.tags.get('arch'), ["x86_64", "ppc64"])


class RunnableToRecipe(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    def test_runnable_to_recipe_noop(self):
        runnable = nrunner.Runnable('noop', None)
        recipe_path = os.path.join(self.tmpdir.name, 'recipe.json')
        runnable.write_json(recipe_path)
        self.assertTrue(os.path.exists(recipe_path))
        loaded_runnable = nrunner.runnable_from_recipe(recipe_path)
        self.assertEqual(loaded_runnable.kind, 'noop')

    def test_runnable_to_recipe_uri(self):
        runnable = nrunner.Runnable('exec', '/bin/true')
        recipe_path = os.path.join(self.tmpdir.name, 'recipe.json')
        runnable.write_json(recipe_path)
        self.assertTrue(os.path.exists(recipe_path))
        loaded_runnable = nrunner.runnable_from_recipe(recipe_path)
        self.assertEqual(loaded_runnable.kind, 'exec')
        self.assertEqual(loaded_runnable.uri, '/bin/true')

    def test_runnable_to_recipe_args(self):
        runnable = nrunner.Runnable('exec', '/bin/sleep', '0.01')
        recipe_path = os.path.join(self.tmpdir.name, 'recipe.json')
        runnable.write_json(recipe_path)
        self.assertTrue(os.path.exists(recipe_path))
        loaded_runnable = nrunner.runnable_from_recipe(recipe_path)
        self.assertEqual(loaded_runnable.kind, 'exec')
        self.assertEqual(loaded_runnable.uri, '/bin/sleep')
        self.assertEqual(loaded_runnable.args, ('0.01', ))

    def tearDown(self):
        self.tmpdir.cleanup()


class Runner(unittest.TestCase):

    def test_runner_noop(self):
        runnable = nrunner.Runnable('noop', None)
        runner = nrunner.runner_from_runnable(runnable)
        results = [status for status in runner.run()]
        last_result = results[-1]
        self.assertEqual(last_result['status'], 'finished')
        self.assertIn('time_end', last_result)

    def test_runner_exec(self):
        runnable = nrunner.Runnable('exec', sys.executable,
                                    '-c', '"import time; time.sleep(0.01)"')
        runner = nrunner.runner_from_runnable(runnable)
        results = [status for status in runner.run()]
        last_result = results[-1]
        self.assertEqual(last_result['status'], 'finished')
        self.assertEqual(last_result['returncode'], 0)
        self.assertEqual(last_result['stdout'], b'')
        self.assertEqual(last_result['stderr'], b'')
        self.assertIn('time_end', last_result)

    def test_runner_exec_test(self):
        runnable = nrunner.Runnable('exec-test', sys.executable,
                                    '-c', '"import time; time.sleep(0.01)"')
        runner = nrunner.runner_from_runnable(runnable)
        results = [status for status in runner.run()]
        last_result = results[-1]
        self.assertEqual(last_result['status'], 'pass')
        self.assertEqual(last_result['returncode'], 0)
        self.assertEqual(last_result['stdout'], b'')
        self.assertEqual(last_result['stderr'], b'')
        self.assertIn('time_end', last_result)

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
