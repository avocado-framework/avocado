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


class RunnerApp(nrunner.BaseRunnerApp):
    PROG_NAME = 'avocado-runner-avocado-instrumented',
    PROG_DESCRIPTION = '*EXPERIMENTAL* N(ext) Runner for avocado-instrumented tests'
    RUNNABLE_KINDS_CAPABLE = {
        'avocado-instrumented': AvocadoInstrumentedTestRunner
    }


def main():
    nrunner.main(RunnerApp)


if __name__ == '__main__':
    main()
