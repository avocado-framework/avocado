import argparse
import io
import json
import subprocess
import time

from . import nrunner
from .tapparser import TapParser
from .tapparser import TestResult


class TAPRunner(nrunner.BaseRunner):
    """Runner for standalone executables treated as TAP

    When creating the Runnable, use the following attributes:

     * kind: should be 'tap';

     * uri: path to a binary to be executed as another process. This must
       provides a TAP output.

     * args: any runnable argument will be given on the command line to the
       binary given by path

     * kwargs: you can specify multiple key=val as kwargs. This will be used as
       environment variables to the process.

    Example:

       runnable = Runnable(kind='tap',
                           uri='tests/foo.sh',
                           'bar', # arg 1
                           DEBUG='false') # kwargs 1 (environment)
    """
    def run(self):
        env = self.runnable.kwargs or None
        process = subprocess.Popen(
            [self.runnable.uri] + list(self.runnable.args),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env)

        while process.poll() is None:
            time.sleep(nrunner.RUNNER_RUN_STATUS_INTERVAL)
            yield {'status': 'running',
                   'timestamp': time.time()}

        stdout = io.TextIOWrapper(process.stdout)
        parser = TapParser(stdout)
        status = 'error'
        for event in parser.parse():
            if isinstance(event, TapParser.Bailout):
                status = 'error'
                break
            elif isinstance(event, TapParser.Error):
                status = 'error'
                break
            elif isinstance(event, TapParser.Test):
                if event.result in (TestResult.XPASS, TestResult.FAIL):
                    status = 'fail'
                    break
                elif event.result == TestResult.SKIP:
                    status = 'skip'
                    break
                else:
                    status = 'pass'

        yield {'status': status,
               'returncode': process.returncode,
               'timestamp': time.time()}


def subcommand_capabilities(_, echo=print):
    data = {"runnables": [k for k in RUNNABLE_KIND_CAPABLE.keys()],
            "commands": [k for k in COMMANDS_CAPABLE.keys()]}
    echo(json.dumps(data))


def subcommand_runnable_run(args, echo=print):
    runnable = nrunner.Runnable.from_args(args)
    runner = nrunner.runner_from_runnable(runnable, RUNNABLE_KIND_CAPABLE)

    for status in runner.run():
        echo(status)


def subcommand_task_run(args, echo=print):
    runnable = nrunner.Runnable.from_args(args)
    task = nrunner.Task(args.get('identifier'), runnable,
                        args.get('status_uri', []))
    task.capables = RUNNABLE_KIND_CAPABLE
    nrunner.task_run(task, echo)


COMMANDS_CAPABLE = {'capabilities': subcommand_capabilities,
                    'runnable-run': subcommand_runnable_run,
                    'task-run': subcommand_task_run}


RUNNABLE_KIND_CAPABLE = {'tap': TAPRunner}


def parse():
    parser = argparse.ArgumentParser(
        prog='avocado-runner-tap',
        description=('*EXPERIMENTAL* N(ext) Runner for executable tests '
                     'that produce TAP'))
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
