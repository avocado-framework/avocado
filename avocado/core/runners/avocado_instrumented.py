import logging
import multiprocessing
import sys
import tempfile
import time
import traceback

from .. import loader, nrunner, output
from ..test import TestID
from ..tree import TreeNode


def _send_message(msg, queue, message_type):
    status = {'type': message_type, 'log': msg}
    queue.put(status)


class RunnerLogHandler(logging.Handler):

    def __init__(self, queue, message_type):
        """
        Runner logger which will put every log to the runner queue

        :param queue: queue for the runner messages
        :type queue: multiprocessing.SimpleQueue
        :param message_type: type of the log
        :type message_type: string
        """
        super().__init__()
        self.queue = queue
        self.message_type = message_type

    def emit(self, record):
        msg = self.format(record)
        _send_message(msg, self.queue, self.message_type)


class StreamToQueue:

    def __init__(self,  queue, message_type):
        """
        Runner Stream which will transfer every  to the runner queue

        :param queue: queue for the runner messages
        :type queue: multiprocessing.SimpleQueue
        :param message_type: type of the log
        :type message_type: string
        """
        self.queue = queue
        self.message_type = message_type

    def write(self, buf):
        _send_message(buf, self.queue, self.message_type)

    def flush(self):
        pass


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
    def _start_logging(runnable, queue):
        log_level = runnable.config.get('job.output.loglevel', logging.DEBUG)
        log_handler = RunnerLogHandler(queue, 'log')
        fmt = '%(asctime)s %(levelname)-5.5s| %(message)s'
        formatter = logging.Formatter(fmt=fmt, datefmt='%H:%M:%S')
        log_handler.setFormatter(formatter)
        log = output.LOG_JOB
        log.addHandler(log_handler)
        log.setLevel(log_level)
        log.propagate = False
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        output.LOG_UI.addHandler(RunnerLogHandler(queue, 'stdout'))

        sys.stdout = StreamToQueue(queue, "stdout")
        sys.stderr = StreamToQueue(queue, "stderr")

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
            test_factory = [klass,
                            {'name': TestID(1, klass_method),
                             'methodName': method,
                             'config': runnable.config,
                             'modulePath': module_path,
                             'params': (TreeNode(), []),
                             'tags': runnable.tags,
                             'run.results_dir': tempfile.mkdtemp(),
                             }]

            AvocadoInstrumentedTestRunner._start_logging(runnable, queue)
            instance = loader.loader.load_test(test_factory)
            early_state = instance.get_state()
            early_state['type'] = "early_state"
            queue.put(early_state)
            instance.run_avocado()
            state = instance.get_state()
            _send_message(state['whiteboard'], queue, 'whiteboard')
            queue.put({'status': 'finished',
                       'result': state['status'].lower()})
        except Exception:
            _send_message(traceback.format_exc().encode('utf-8'), queue,
                          'stderr')
            queue.put({'status': 'finished', 'result': 'error'})

    def run(self):
        yield self.prepare_status('started')
        try:
            queue = multiprocessing.SimpleQueue()
            process = multiprocessing.Process(target=self._run_avocado,
                                              args=(self.runnable, queue))

            process.start()

            time_started = time.monotonic()

            early_status = {}
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
                        yield self.prepare_status('running')
                    if (now - time_started) > timeout:
                        process.terminate()
                        status = early_status
                        status['result'] = 'interrupted'
                        if 'name' in status:
                            del status['name']
                        if 'time_start' in status:
                            del status['time_start']
                        yield self.prepare_status('finished', status)
                        break
                else:
                    message = queue.get()
                    if message.get('status') == 'finished':
                        yield self.prepare_status('finished', message)
                        break
                    elif message.get('type') == 'early_state':
                        early_status = message
                        timeout = float(early_status.get('timeout') or
                                        self.DEFAULT_TIMEOUT)
                    else:
                        yield self.prepare_status('running', message)
        except Exception:
            yield self.prepare_status('running',
                                      {'type': 'stderr',
                                       'log': traceback.format_exc().encode(
                                           'utf-8')})
            yield self.prepare_status('finished', {'result': 'error'})


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
