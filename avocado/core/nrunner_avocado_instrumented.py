import argparse
import json
import multiprocessing
import tempfile
import time

from . import job
from . import loader
from . import nrunner
from .test import TestID
from .tree import TreeNode


class AvocadoInstrumentedTestRunner(nrunner.BaseRunner):
    """
    Runner for Avocado INSTRUMENTED tests

    Runnable attributes usage:

     * uri: path to a test file, combined with an Avocado.Test
       inherited class name and method.  The test file path and
       class and method names should be separated by a ":".  One
       example of a valid uri is "mytest.py:Class.test_method".

     * args: not used
    """

    @staticmethod
    def _run_avocado(runnable, queue):
        # This assumes that a proper resolution (see resolver module)
        # was performed, and that a URI contains:
        # 1) path to python module
        # 2) class
        # 3) method
        #
        # To be defined: if the resolution uri should be composed like
        # this, or broken down and stored into other data fields
        module_path, klass_method = runnable.uri.split(':', 1)

        klass, method = klass_method.split('.', 1)
        test_factory = [klass,
                        {'name': TestID(1, klass_method),
                         'methodName': method,
                         'base_logdir': tempfile.mkdtemp(),
                         'job': job.Job(),
                         'modulePath': module_path,
                         'params': (TreeNode(), []),
                         'tags': runnable.tags}]

        instance = loader.loader.load_test(test_factory)
        instance.run_avocado()
        state = instance.get_state()
        # This should probably be done in a translator
        if 'status' in state:
            state['status'] = state['status'].lower()
        # This is a hack because the name is a TestID instance that can not
        # at this point be converted to JSON
        if 'name' in state:
            del state['name']
        if 'time_start' in state:
            del state['time_start']
        queue.put(state)

    def run(self):
        queue = multiprocessing.SimpleQueue()
        process = multiprocessing.Process(target=self._run_avocado,
                                          args=(self.runnable, queue))
        time_start = time.time()
        time_start_sent = False
        process.start()

        last_status = None
        while queue.empty():
            time.sleep(nrunner.RUNNER_RUN_CHECK_INTERVAL)
            now = time.time()
            if last_status is None or now > last_status + nrunner.RUNNER_RUN_STATUS_INTERVAL:
                last_status = now
                if not time_start_sent:
                    time_start_sent = True
                    yield {'status': 'running',
                           'time_start': time_start}
                yield {'status': 'running'}

        yield queue.get()


def subcommand_capabilities(_, echo=print):
    data = {"runnables": [k for k in RUNNABLE_KIND_CAPABLE.keys()],
            "commands": [k for k in COMMANDS_CAPABLE.keys()]}
    echo(json.dumps(data))


def subcommand_runnable_run(args, echo=print):
    runnable = nrunner.runnable_from_args(args)
    runner = nrunner.runner_from_runnable(runnable, RUNNABLE_KIND_CAPABLE)

    for status in runner.run():
        echo(status)


def subcommand_task_run(args, echo=print):
    runnable = nrunner.runnable_from_args(args)
    task = nrunner.Task(args.get('identifier'), runnable,
                        args.get('status_uri', []))
    task.capables = RUNNABLE_KIND_CAPABLE
    nrunner.task_run(task, echo)


COMMANDS_CAPABLE = {'capabilities': subcommand_capabilities,
                    'runnable-run': subcommand_runnable_run,
                    'task-run': subcommand_task_run}


RUNNABLE_KIND_CAPABLE = {'avocado-instrumented': AvocadoInstrumentedTestRunner}


def parse():
    parser = argparse.ArgumentParser(
        prog='avocado-runner-avocado-instrumented',
        description='*EXPERIMENTAL* N(ext) Runner for avocado-instrumented tests')
    subcommands = parser.add_subparsers(dest='subcommand')
    subcommands.required = True
    subcommands.add_parser('capabilities')
    runnable_run_parser = subcommands.add_parser('runnable-run')
    for arg in nrunner.CMD_RUNNABLE_RUN_ARGS:
        runnable_run_parser.add_argument(*arg[0], **arg[1])
    runnable_task_parser = subcommands.add_parser('task-run')
    for arg in nrunner.CMD_TASK_RUN_ARGS:
        runnable_task_parser.add_argument(*arg[0], **arg[1])
    return parser.parse_args()


def main():
    args = vars(parse())
    subcommand = args.get('subcommand')
    kallable = COMMANDS_CAPABLE.get(subcommand)
    if kallable is not None:
        kallable(args)


if __name__ == '__main__':
    main()
