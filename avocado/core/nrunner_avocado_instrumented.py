import multiprocessing
import tempfile
import time

from . import job, loader, nrunner
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
                         'job': job.Job(),
                         'modulePath': module_path,
                         'params': (TreeNode(), []),
                         'tags': runnable.tags,
                         'run.results_dir': tempfile.mkdtemp(),
                         }]

        instance = loader.loader.load_test(test_factory)
        instance.run_avocado()
        state = instance.get_state()
        # This should probably be done in a translator
        if 'status' in state:
            status = state['status'].lower()
            if status in ['pass', 'fail', 'skip', 'error']:
                state['result'] = status
                state['status'] = 'finished'
            else:
                state['status'] = 'running'

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

        process.start()

        yield self.prepare_status('started')
        most_current_execution_state_time = None
        while queue.empty():
            time.sleep(nrunner.RUNNER_RUN_CHECK_INTERVAL)
            now = time.monotonic()
            if most_current_execution_state_time is not None:
                next_execution_state_mark = (most_current_execution_state_time +
                                             nrunner.RUNNER_RUN_STATUS_INTERVAL)
            if (most_current_execution_state_time is None or
                    now > next_execution_state_mark):
                most_current_execution_state_time = now
                yield self.prepare_status('running')

        status = queue.get()
        status['time'] = time.monotonic()
        yield status


class RunnerApp(nrunner.BaseRunnerApp):
    PROG_NAME = 'avocado-runner-avocado-instrumented'
    PROG_DESCRIPTION = 'nrunner application for avocado-instrumented tests'
    RUNNABLE_KINDS_CAPABLE = {
        'avocado-instrumented': AvocadoInstrumentedTestRunner
    }


def main():
    nrunner.main(RunnerApp)


if __name__ == '__main__':
    main()
