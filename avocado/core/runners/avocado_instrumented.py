import multiprocessing
import tempfile
import time
import traceback

from .. import loader, nrunner
from ..test import TestID
from ..tree import TreeNode
from .utils import messages


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
    DEFAULT_TIMEOUT = 86400

    @staticmethod
    def _run_avocado(runnable, queue):
        try:
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

            # inject the run.test_parameters option in the Test params
            # this handles the -p command-line argument
            params = TreeNode().get_node("/", True)
            params.value = dict(runnable.config.get('run.test_parameters', []))

            test_factory = [klass,
                            {'name': TestID(1, klass_method),
                             'methodName': method,
                             'config': runnable.config,
                             'modulePath': module_path,
                             'params': (params, ["/"]),
                             'tags': runnable.tags,
                             'run.results_dir': tempfile.mkdtemp(prefix=".avocado-task"),
                             }]

            messages.start_logging(runnable.config, queue)
            instance = loader.loader.load_test(test_factory)
            early_state = instance.get_state()
            early_state['type'] = "early_state"
            queue.put(early_state)
            instance.run_avocado()
            state = instance.get_state()
            fail_reason = state.get('fail_reason')
            queue.put(messages.WhiteboardMessage.get(state['whiteboard']))
            queue.put(messages.FinishedMessage.get(state['status'].lower(),
                                                   fail_reason=fail_reason))
        except Exception as e:
            queue.put(messages.StderrMessage.get(traceback.format_exc()))
            queue.put(messages.FinishedMessage.get('error', fail_reason=str(e)))

    def run(self):
        yield messages.StartedMessage.get()
        try:
            queue = multiprocessing.SimpleQueue()
            process = multiprocessing.Process(target=self._run_avocado,
                                              args=(self.runnable, queue))

            process.start()

            time_started = time.monotonic()

            timeout = float(self.DEFAULT_TIMEOUT)
            most_current_execution_state_time = None
            while True:
                time.sleep(nrunner.RUNNER_RUN_CHECK_INTERVAL)
                now = time.monotonic()
                if queue.empty():
                    if most_current_execution_state_time is not None:
                        next_execution_state_mark = (most_current_execution_state_time +
                                                     nrunner.RUNNER_RUN_STATUS_INTERVAL)
                    if (most_current_execution_state_time is None or
                            now > next_execution_state_mark):
                        most_current_execution_state_time = now
                        yield messages.RunningMessage.get()
                    if (now - time_started) > timeout:
                        process.terminate()
                        yield messages.FinishedMessage.get('interrupted',
                                                           'timeout')
                        break
                else:
                    message = queue.get()
                    if message.get('type') == 'early_state':
                        timeout = float(message.get('timeout') or
                                        self.DEFAULT_TIMEOUT)
                    else:
                        yield message
                    if message.get('status') == 'finished':
                        break
        except Exception as e:
            yield messages.StderrMessage.get(traceback.format_exc())
            yield messages.FinishedMessage.get('error', fail_reason=str(e))


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
