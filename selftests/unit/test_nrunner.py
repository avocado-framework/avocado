import os
import sys
import tempfile
import unittest.mock

from avocado.core import nrunner
from avocado.core.runners import tap as runner_tap
from selftests.utils import skipUnlessPathExists, temp_dir_prefix


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
            runnable = nrunner.Runnable.from_recipe("fake_path")
        self.assertEqual(runnable.kind, "noop")

    def test_recipe_exec(self):
        open_mocked = unittest.mock.mock_open(
            read_data=('{"kind": "exec", "uri": "/bin/sh", '
                       '"args": ["/etc/profile"], '
                       '"kwargs": {"TERM": "vt3270"}}'))
        with unittest.mock.patch("builtins.open", open_mocked):
            runnable = nrunner.Runnable.from_recipe("fake_path")
        self.assertEqual(runnable.kind, "exec")
        self.assertEqual(runnable.uri, "/bin/sh")
        self.assertEqual(runnable.args, ("/etc/profile",))
        self.assertEqual(runnable.kwargs, {"TERM": "vt3270"})

    def test_identifier_args(self):
        config = {'runner.identifier_format': '{uri}-{args[0]}'}
        runnable = nrunner.Runnable('exec-text', 'uri', 'arg1', 'arg2',
                                    config=config)
        self.assertEqual(runnable.identifier, 'uri-arg1')

    def test_runnable_command_args(self):
        runnable = nrunner.Runnable('noop', 'uri', 'arg1', 'arg2')
        actual_args = runnable.get_command_args()
        exp_args = ['-k', 'noop', '-u', 'uri', '-a', 'arg1', '-a', 'arg2']
        self.assertEqual(actual_args, exp_args)

    def test_get_dict(self):
        runnable = nrunner.Runnable('noop', '_uri_', 'arg1', 'arg2')
        self.assertEqual(runnable.get_dict(),
                         {'kind': 'noop', 'uri': '_uri_',
                          'args': ('arg1', 'arg2'),
                          'config': {}})

    def test_get_json(self):
        runnable = nrunner.Runnable('noop', '_uri_', 'arg1', 'arg2')
        expected = ('{"kind": "noop", '
                    '"uri": "_uri_", '
                    '"config": {}, '
                    '"args": ["arg1", "arg2"]}')
        self.assertEqual(runnable.get_json(), expected)

    def test_runner_from_runnable_error(self):
        runnable = nrunner.Runnable('unsupported_kind', '')
        try:
            runnable.pick_runner_class()
        except ValueError as e:
            self.assertEqual(str(e), 'Unsupported kind of runnable: unsupported_kind')


class RunnableFromCommandLineArgs(unittest.TestCase):

    def test_noop(self):
        parsed_args = {'kind': 'noop', 'uri': None}
        runnable = nrunner.Runnable.from_args(parsed_args)
        self.assertEqual(runnable.kind, 'noop')
        self.assertIsNone(runnable.uri)

    def test_exec_args(self):
        parsed_args = {'kind': 'exec', 'uri': '/path/to/executable',
                       'arg': ['-a', '-b', '-c']}
        runnable = nrunner.Runnable.from_args(parsed_args)
        self.assertEqual(runnable.kind, 'exec')
        self.assertEqual(runnable.uri, '/path/to/executable')
        self.assertEqual(runnable.args, ('-a', '-b', '-c'))
        self.assertEqual(runnable.kwargs, {})

    def test_exec_args_kwargs(self):
        parsed_args = {'kind': 'exec', 'uri': '/path/to/executable',
                       'arg': ['-a', '-b', '-c'],
                       'kwargs': [('DEBUG', '1'), ('LC_ALL', 'C')]}
        runnable = nrunner.Runnable.from_args(parsed_args)
        self.assertEqual(runnable.kind, 'exec')
        self.assertEqual(runnable.uri, '/path/to/executable')
        self.assertEqual(runnable.args, ('-a', '-b', '-c'))
        self.assertEqual(runnable.kwargs.get('DEBUG'), '1')
        self.assertEqual(runnable.kwargs.get('LC_ALL'), 'C')

    def test_kwargs_json_empty_dict(self):
        parsed_args = {'kind': 'noop', 'uri': None,
                       'kwargs': [('empty', 'json:{}')]}
        runnable = nrunner.Runnable.from_args(parsed_args)
        self.assertEqual(runnable.kind, 'noop')
        self.assertIsNone(runnable.uri)
        self.assertEqual(runnable.kwargs.get('empty'), {})

    def test_kwargs_json_dict(self):
        parsed_args = {
            'kind': 'noop', 'uri': None,
            'kwargs': [('tags', 'json:{"arch": ["x86_64", "ppc64"]}'),
                       ('hi', 'json:"hello"')]
        }
        runnable = nrunner.Runnable.from_args(parsed_args)
        self.assertEqual(runnable.kind, 'noop')
        self.assertIsNone(runnable.uri)
        self.assertEqual(runnable.kwargs.get('hi'), 'hello')
        self.assertEqual(runnable.tags.get('arch'), ["x86_64", "ppc64"])


class RunnableToRecipe(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(self)
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    def test_runnable_to_recipe_noop(self):
        runnable = nrunner.Runnable('noop', None)
        recipe_path = os.path.join(self.tmpdir.name, 'recipe.json')
        runnable.write_json(recipe_path)
        self.assertTrue(os.path.exists(recipe_path))
        loaded_runnable = nrunner.Runnable.from_recipe(recipe_path)
        self.assertEqual(loaded_runnable.kind, 'noop')

    def test_runnable_to_recipe_uri(self):
        runnable = nrunner.Runnable('exec', '/bin/true')
        recipe_path = os.path.join(self.tmpdir.name, 'recipe.json')
        runnable.write_json(recipe_path)
        self.assertTrue(os.path.exists(recipe_path))
        loaded_runnable = nrunner.Runnable.from_recipe(recipe_path)
        self.assertEqual(loaded_runnable.kind, 'exec')
        self.assertEqual(loaded_runnable.uri, '/bin/true')

    def test_runnable_to_recipe_args(self):
        runnable = nrunner.Runnable('exec', '/bin/sleep', '0.01')
        recipe_path = os.path.join(self.tmpdir.name, 'recipe.json')
        runnable.write_json(recipe_path)
        self.assertTrue(os.path.exists(recipe_path))
        loaded_runnable = nrunner.Runnable.from_recipe(recipe_path)
        self.assertEqual(loaded_runnable.kind, 'exec')
        self.assertEqual(loaded_runnable.uri, '/bin/sleep')
        self.assertEqual(loaded_runnable.args, ('0.01', ))

    def tearDown(self):
        self.tmpdir.cleanup()


class Runner(unittest.TestCase):

    def test_runner_noop(self):
        runnable = nrunner.Runnable('noop', None)
        runner_klass = runnable.pick_runner_class()
        runner = runner_klass(runnable)
        results = [status for status in runner.run()]
        last_result = results[-1]
        self.assertEqual(last_result['status'], 'finished')
        self.assertIn('time', last_result)

    def test_runner_exec(self):
        runnable = nrunner.Runnable('exec-test', sys.executable,
                                    '-c', 'import time; time.sleep(0.01)')
        runner_klass = runnable.pick_runner_class()
        runner = runner_klass(runnable)
        results = [status for status in runner.run()]
        stdout_result = results[-3]
        stderr_result = results[-2]
        last_result = results[-1]
        self.assertEqual(stdout_result['type'], 'stdout')
        self.assertEqual(stdout_result['log'], b'')
        self.assertEqual(stderr_result['type'], 'stderr')
        self.assertEqual(stderr_result['log'], b'')
        self.assertEqual(last_result['status'], 'finished')
        self.assertEqual(last_result['returncode'], 0)
        self.assertIn('time', last_result)

    def test_runner_exec_test_ok(self):
        runnable = nrunner.Runnable('exec-test', sys.executable,
                                    '-c', 'import time; time.sleep(0.01)')
        runner_klass = runnable.pick_runner_class()
        runner = runner_klass(runnable)
        results = [status for status in runner.run()]
        stdout_result = results[-3]
        stderr_result = results[-2]
        last_result = results[-1]
        self.assertEqual(stdout_result['type'], 'stdout')
        self.assertEqual(stdout_result['log'], b'')
        self.assertEqual(stderr_result['type'], 'stderr')
        self.assertEqual(stderr_result['log'], b'')
        self.assertEqual(last_result['status'], 'finished')
        self.assertEqual(last_result['result'], 'pass')
        self.assertEqual(last_result['returncode'], 0)
        self.assertIn('time', last_result)

    @skipUnlessPathExists('/bin/false')
    def test_runner_exec_test_fail(self):
        runnable = nrunner.Runnable('exec-test', '/bin/false')
        runner_klass = runnable.pick_runner_class()
        runner = runner_klass(runnable)
        results = [status for status in runner.run()]
        stdout_result = results[-3]
        stderr_result = results[-2]
        last_result = results[-1]
        self.assertEqual(stdout_result['type'], 'stdout')
        self.assertEqual(stdout_result['log'], b'')
        self.assertEqual(stderr_result['type'], 'stderr')
        self.assertEqual(stderr_result['log'], b'')
        self.assertEqual(last_result['status'], 'finished')
        self.assertEqual(last_result['result'], 'fail')
        self.assertEqual(last_result['returncode'], 1)
        self.assertIn('time', last_result)

    def test_runner_python_unittest_error(self):
        runnable = nrunner.Runnable('python-unittest', 'error')
        runner_klass = runnable.pick_runner_class()
        runner = runner_klass(runnable)
        results = [status for status in runner.run()]
        output = ("Invalid URI: could not be converted to an unittest "
                  "dotted name.")
        result = results[-1]
        self.assertEqual(result['status'], 'finished')
        self.assertEqual(result['result'], 'error')
        self.assertEqual(result['output'], output)

    def test_runner_python_unittest_empty_uri_error(self):
        runnable = nrunner.Runnable('python-unittest', '')
        runner_klass = runnable.pick_runner_class()
        runner = runner_klass(runnable)
        results = [status for status in runner.run()]
        output = ("Invalid URI: could not be converted to an unittest "
                  "dotted name.")
        result = results[-1]
        self.assertEqual(result['status'], 'finished')
        self.assertEqual(result['result'], 'error')
        self.assertEqual(result['output'], output)


class RunnerTmp(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(self)
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    @skipUnlessPathExists('/bin/sh')
    def test_runner_tap_fail(self):
        tap_script = """#!/bin/sh
echo '1..2'
echo '# Defining an basic test'
echo 'ok 1 - description 1'
echo 'not ok 2 - description 2'"""
        tap_path = os.path.join(self.tmpdir.name, 'tap.sh')

        with open(tap_path, 'w') as fp:
            fp.write(tap_script)

        runnable = nrunner.Runnable('tap', '/bin/sh', tap_path)
        runner = runner_tap.TAPRunner(runnable)
        results = [status for status in runner.run()]
        last_result = results[-1]
        self.assertEqual(last_result['status'], 'finished')
        self.assertEqual(last_result['result'], 'fail')
        self.assertEqual(last_result['returncode'], 0)

    @skipUnlessPathExists('/bin/sh')
    def test_runner_tap_ok(self):
        tap_script = """#!/bin/sh
echo '1..2'
echo '# Defining an basic test'
echo 'ok 1 - description 1'
echo 'ok 2 - description 2'"""
        tap_path = os.path.join(self.tmpdir.name, 'tap.sh')

        with open(tap_path, 'w') as fp:
            fp.write(tap_script)

        runnable = nrunner.Runnable('tap', '/bin/sh', tap_path)
        runner = runner_tap.TAPRunner(runnable)
        results = [status for status in runner.run()]
        last_result = results[-1]
        self.assertEqual(last_result['status'], 'finished')
        self.assertEqual(last_result['result'], 'pass')
        self.assertEqual(last_result['returncode'], 0)

    @skipUnlessPathExists('/bin/sh')
    def test_runner_tap_skip(self):
        tap_script = """#!/bin/sh
echo '1..2'
echo '# Defining an basic test'
echo 'ok 1 - # SKIP description 1'
echo 'ok 2 - description 2'"""
        tap_path = os.path.join(self.tmpdir.name, 'tap.sh')

        with open(tap_path, 'w') as fp:
            fp.write(tap_script)

        runnable = nrunner.Runnable('tap', '/bin/sh', tap_path)
        runner = runner_tap.TAPRunner(runnable)
        results = [status for status in runner.run()]
        last_result = results[-1]
        self.assertEqual(last_result['status'], 'finished')
        self.assertEqual(last_result['result'], 'skip')
        self.assertEqual(last_result['returncode'], 0)

    @skipUnlessPathExists('/bin/sh')
    def test_runner_tap_bailout(self):
        tap_script = """#!/bin/sh
echo '1..2'
echo '# Defining an basic test'
echo 'Bail out! - description 1'
echo 'ok 2 - description 2'"""
        tap_path = os.path.join(self.tmpdir.name, 'tap.sh')

        with open(tap_path, 'w') as fp:
            fp.write(tap_script)

        runnable = nrunner.Runnable('tap', '/bin/sh', tap_path)
        runner = runner_tap.TAPRunner(runnable)
        results = [status for status in runner.run()]
        last_result = results[-1]
        self.assertEqual(last_result['status'], 'finished')
        self.assertEqual(last_result['result'], 'error')
        self.assertEqual(last_result['returncode'], 0)

    @skipUnlessPathExists('/bin/sh')
    def test_runner_tap_error(self):
        tap_script = """#!/bin/sh
echo '1..2'
echo '# Defining an basic test'
echo 'error - description 1'
echo 'ok 2 - description 2'"""
        tap_path = os.path.join(self.tmpdir.name, 'tap.sh')

        with open(tap_path, 'w') as fp:
            fp.write(tap_script)

        runnable = nrunner.Runnable('tap', '/bin/sh', tap_path)
        runner = runner_tap.TAPRunner(runnable)
        results = [status for status in runner.run()]
        last_result = results[-1]
        self.assertEqual(last_result['status'], 'finished')
        self.assertEqual(last_result['result'], 'error')
        self.assertEqual(last_result['returncode'], 0)

    def tearDown(self):
        self.tmpdir.cleanup()


@skipUnlessPathExists('/bin/sh')
class RunnerCommandSelection(unittest.TestCase):

    def setUp(self):
        self.runnable = nrunner.Runnable('mykind',
                                         'test_runner_command_selection')

    def test_is_task_kind_supported(self):
        cmd = ['sh', '-c',
               'test $0 = capabilities && '
               'echo -n {\\"runnables\\": [\\"mykind\\"]}']
        self.assertTrue(self.runnable.is_kind_supported_by_runner_command(cmd))

    def test_is_task_kind_supported_other_kind(self):
        cmd = ['sh', '-c',
               'test $0 = capabilities && '
               'echo -n {\\"runnables\\": [\\"otherkind\\"]}']
        self.assertFalse(self.runnable.is_kind_supported_by_runner_command(cmd))

    def test_is_task_kind_supported_no_output(self):
        cmd = ['sh', '-c', 'echo -n ""']
        self.assertFalse(self.runnable.is_kind_supported_by_runner_command(cmd))


class PickRunner(unittest.TestCase):

    def setUp(self):
        self.runnable = nrunner.Runnable('lets-image-a-kind',
                                         'test_pick_runner_command')

    def test_pick_runner_command(self):
        runner = ['avocado-runner-lets-image-a-kind']
        known = {'lets-image-a-kind': runner}
        self.assertEqual(self.runnable.pick_runner_command(known), runner)

    def test_pick_runner_command_empty(self):
        self.assertFalse(self.runnable.pick_runner_command({}))


class Task(unittest.TestCase):

    def test_default_category(self):
        runnable = nrunner.Runnable('noop', 'noop_uri')
        task = nrunner.Task(runnable, 'task_id')
        self.assertEqual(task.category, 'test')

    def test_set_category(self):
        runnable = nrunner.Runnable('noop', 'noop_uri')
        task = nrunner.Task(runnable, 'task_id', category='new_category')
        self.assertEqual(task.category, 'new_category')


if __name__ == '__main__':
    unittest.main()
