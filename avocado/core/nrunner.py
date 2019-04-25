import argparse
import io
import json
import multiprocessing
import subprocess
import time
import unittest

#: The amount of time between each internal status check
RUNNER_RUN_CHECK_INTERVAL = 0.01

#: The amount of time between a status report from a runner that
#: performs its work asynchronously
RUNNER_RUN_STATUS_INTERVAL = 0.5


class Runnable:
    """
    Describes an entity that be executed in the context of a task

    A instance of :class:`BaseRunner` is the entity that will actually
    execute a runnable.
    """
    def __init__(self, kind, uri=None, *args, **kwargs):
        self.kind = kind
        self.uri = uri
        self.args = args
        self.kwargs = kwargs


def runnable_from_recipe(recipe_path):
    """
    Returns a runnable from a runnable recipe file
    """
    with open(recipe_path) as recipe_file:
        recipe = json.load(recipe_file)
    return Runnable(recipe.get('kind'),
                    recipe.get('uri'),
                    *recipe.get('args', ()))


class BaseRunner:
    """
    Base interface for a Runner
    """

    def __init__(self, runnable):
        self.runnable = runnable

    def run(self):
        yield {}


class NoOpRunner(BaseRunner):
    """
    Sample runner that performs no action before reporting FINISHED status
    """
    def run(self):
        yield {'status': 'finished'}


class ExecRunner(BaseRunner):
    """
    Runner for standalone executables with or without arguments
    """
    def run(self):
        process = subprocess.Popen(
            [self.runnable.uri] + list(self.runnable.args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        last_status = None
        while process.poll() is None:
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)
            now = time.time()
            if last_status is None or now > last_status + RUNNER_RUN_STATUS_INTERVAL:
                last_status = now
                yield {'status': 'running'}

        stdout = process.stdout.read()
        process.stdout.close()
        stderr = process.stderr.read()
        process.stderr.close()

        yield {'status': 'finished',
               'returncode': process.returncode,
               'stdout': stdout,
               'stderr': stderr}


class ExecTestRunner(ExecRunner):
    def run(self):
        for status in super(ExecTestRunner, self).run():
            if 'returncode' in status:
                if status['returncode'] == 0:
                    status['status'] = 'pass'
                else:
                    status['status'] = 'fail'
            yield status


class PythonUnittestRunner(BaseRunner):
    """
    Runner for Python unittests

    The runnable uri is used as the test name that the native unittest
    TestLoader will use to find the test.  A native unittest test
    runner (TextTextRunner) will be used to execute the test.
    """
    @staticmethod
    def _run_unittest(uri, queue):
        stream = io.StringIO()
        suite = unittest.TestLoader().loadTestsFromName(uri)
        runner = unittest.TextTestRunner(stream=stream, verbosity=0)
        unittest_result = runner.run(suite)

        if len(unittest_result.errors) > 0:
            status = 'error'
        elif len(unittest_result.failures) > 0:
            status = 'fail'
        elif len(unittest_result.skipped) > 0:
            status = 'skip'
        else:
            status = 'pass'

        stream.seek(0)
        result = {'status': status,
                  'output': stream.read()}
        stream.close()
        queue.put(result)

    def run(self):
        queue = multiprocessing.SimpleQueue()
        process = multiprocessing.Process(target=self._run_unittest,
                                          args=(self.runnable.uri, queue))
        process.start()

        last_status = None
        while queue.empty():
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)
            now = time.time()
            if last_status is None or now > last_status + RUNNER_RUN_STATUS_INTERVAL:
                last_status = now
                yield {'status': 'running'}

        yield queue.get()


def runner_from_runnable(runnable):
    """
    Gets a Runner instance from a Runnable
    """
    if runnable.kind == 'noop':
        return NoOpRunner(runnable)
    if runnable.kind == 'exec':
        return ExecRunner(runnable)
    if runnable.kind == 'exec-test':
        return ExecTestRunner(runnable)
    if runnable.kind == 'python-unittest':
        return PythonUnittestRunner(runnable)


CMD_RUNNABLE_RUN_ARGS = (
    (("-k", "--kind"),
     {'type': str, 'required': True, 'help': 'Kind of runnable'}),

    (("-u", "--uri"),
     {'type': str, 'default': None, 'help': 'URI of runnable'}),

    (("-a", "--arg"),
     {'action': "append", 'default': [], 'help': 'Positional arguments to runnable'})
    )


def runnable_from_args(args):
    return Runnable(getattr(args, 'kind'),
                    getattr(args, 'uri'),
                    *getattr(args, 'arg', ()))


def subcommand_runnable_run(args, echo=print):
    runnable = runnable_from_args(args)
    runner = runner_from_runnable(runnable)

    for status in runner.run():
        echo(status)


CMD_RUNNABLE_RUN_RECIPE_ARGS = (
    (("recipe", ),
     {'type': str, 'help': 'Path to the runnable recipe file'}),
    )


def subcommand_runnable_run_recipe(args, echo=print):
    runnable = runnable_from_recipe(getattr(args, 'recipe'))
    runner = runner_from_runnable(runnable)

    for status in runner.run():
        echo(status)


def parse():
    parser = argparse.ArgumentParser(prog='nrunner')
    subcommands = parser.add_subparsers(dest='subcommand')
    subcommands.required = True
    runnable_run_parser = subcommands.add_parser('runnable-run')
    for arg in CMD_RUNNABLE_RUN_ARGS:
        runnable_run_parser.add_argument(*arg[0], **arg[1])
    runnable_run_recipe_parser = subcommands.add_parser('runnable-run-recipe')
    for arg in CMD_RUNNABLE_RUN_RECIPE_ARGS:
        runnable_run_recipe_parser.add_argument(*arg[0], **arg[1])
    return parser.parse_args()


def main():
    args = parse()
    if args.subcommand == 'runnable-run':
        subcommand_runnable_run(args)
    if args.subcommand == 'runnable-run-recipe':
        subcommand_runnable_run_recipe(args)


if __name__ == '__main__':
    main()
