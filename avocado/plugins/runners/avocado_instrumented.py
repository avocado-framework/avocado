import logging
import multiprocessing
import os
import sys
import tempfile
import time
import traceback

from avocado.core import output
from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import (
    RUNNER_RUN_CHECK_INTERVAL,
    RUNNER_RUN_STATUS_INTERVAL,
    BaseRunner,
)
from avocado.core.streams import BUILTIN_STREAMS
from avocado.core.test import TestID
from avocado.core.tree import TreeNodeEnvOnly
from avocado.core.utils import loader, messages
from avocado.core.varianter import is_empty_variant


class RunnerLogHandler(logging.Handler):
    def __init__(self, queue, message_type, kwargs=None):
        """
        Runner logger which will put every log to the runner queue

        :param queue: queue for the runner messages
        :type queue: multiprocessing.SimpleQueue
        :param message_type: type of the log
        :type message_type: string
        """
        super().__init__()
        self.queue = queue
        self.message = messages.SUPPORTED_TYPES[message_type]
        self.kwargs = kwargs or {}

    def emit(self, record):
        msg = self.format(record)
        self.queue.put(self.message.get(msg, **self.kwargs))


class StreamToQueue:
    def __init__(self, queue, message_type):
        """
        Runner Stream which will transfer data to the runner queue

        :param queue: queue for the runner messages
        :type queue: multiprocessing.SimpleQueue
        :param message_type: type of the log
        :type message_type: string
        """
        self.queue = queue
        self.message = messages.SUPPORTED_TYPES[message_type]

    def write(self, buf):
        self.queue.put(self.message.get(buf))

    def flush(self):
        pass


class AvocadoInstrumentedTestRunner(BaseRunner):
    """
    Runner for Avocado INSTRUMENTED tests

    Runnable attributes usage:

     * uri: path to a test file, combined with an Avocado.Test
       inherited class name and method.  The test file path and
       class and method names should be separated by a ":".  One
       example of a valid uri is "mytest.py:Class.test_method".

     * args: not used
    """

    name = "avocado-instrumented"
    description = "Runner for Avocado INSTRUMENTED tests"

    CONFIGURATION_USED = [
        "run.test_parameters",
        "datadir.paths.cache_dirs",
        "core.show",
        "job.output.loglevel",
        "job.run.store_logging_stream",
    ]

    DEFAULT_TIMEOUT = 86400

    @staticmethod
    def _create_params(runnable):
        """Create params for the test"""
        if runnable.variant is None:
            return None

        # rebuild the variant tree
        variant_tree_nodes = [
            TreeNodeEnvOnly(path, env) for path, env in runnable.variant["variant"]
        ]

        if not is_empty_variant(variant_tree_nodes):
            tree_nodes = variant_tree_nodes
            paths = runnable.variant["paths"]
            return tree_nodes, paths

    @staticmethod
    def _start_logging(config, queue):
        """Helper method for connecting the avocado logging with avocado messages.

        It will add the log Handlers to the :mod:`avocado.core.output` loggers,
        which will convert the logs to the avocado messages and sent them to
        processing queue.

        :param config: avocado configuration
        :type config: dict
        :param queue: queue for the runner messages
        :type queue: multiprocessing.SimpleQueue
        """

        def split_loggers_and_levels(enabled_loggers, default_level):
            for logger_level_split in map(lambda x: x.split(":"), enabled_loggers):
                logger_name, *level = logger_level_split
                yield logger_name, level[0] if len(level) > 0 else default_level

        log_level = config.get("job.output.loglevel", logging.DEBUG)
        log_handler = RunnerLogHandler(queue, "log")
        fmt = "%(asctime)s %(name)s %(levelname)-5.5s| %(message)s"
        formatter = logging.Formatter(fmt=fmt)
        log_handler.setFormatter(formatter)

        # main log = 'avocado'
        logger = logging.getLogger("avocado")
        logger.addHandler(log_handler)
        logger.setLevel(log_level)
        logger.propagate = False

        # LOG_JOB = 'avocado.test'
        log = output.LOG_JOB
        log.addHandler(log_handler)
        log.setLevel(log_level)
        log.propagate = False

        # LOG_UI = 'avocado.app'
        output.LOG_UI.addHandler(RunnerLogHandler(queue, "stdout"))

        sys.stdout = StreamToQueue(queue, "stdout")
        sys.stderr = StreamToQueue(queue, "stderr")

        # output custom test loggers
        enabled_loggers = config.get("core.show")
        output_handler = RunnerLogHandler(queue, "output")
        output_handler.setFormatter(logging.Formatter(fmt="%(name)s: %(message)s"))
        user_streams = [
            user_streams
            for user_streams in enabled_loggers
            if user_streams not in BUILTIN_STREAMS
        ]
        for user_stream, level in split_loggers_and_levels(user_streams, log_level):
            custom_logger = logging.getLogger(user_stream)
            custom_logger.addHandler(output_handler)
            custom_logger.setLevel(level)

        # store custom test loggers
        enabled_loggers = config.get("job.run.store_logging_stream")
        for enabled_logger, level in split_loggers_and_levels(
            enabled_loggers, log_level
        ):
            store_stream_handler = RunnerLogHandler(
                queue, "file", {"path": enabled_logger}
            )
            store_stream_handler.setFormatter(formatter)
            output_logger = logging.getLogger(enabled_logger)
            output_logger.addHandler(store_stream_handler)
            output_logger.setLevel(level)

            if not enabled_logger.startswith("avocado."):
                output_logger.addHandler(log_handler)
                output_logger.propagate = False

    @classmethod
    def _run_avocado(cls, runnable, queue):
        try:
            # This assumes that a proper resolution (see resolver module)
            # was performed, and that a URI contains:
            # 1) path to python module
            # 2) class
            # 3) method
            #
            # To be defined: if the resolution uri should be composed like
            # this, or broken down and stored into other data fields
            module_path, klass_method = runnable.uri.split(":", 1)

            klass, method = klass_method.split(".", 1)

            params = AvocadoInstrumentedTestRunner._create_params(runnable)
            result_dir = runnable.output_dir or tempfile.mkdtemp(prefix=".avocado-task")
            test_factory = [
                klass,
                {
                    "name": TestID(1, runnable.uri, runnable.variant),
                    "methodName": method,
                    "config": runnable.config,
                    "modulePath": module_path,
                    "params": params,
                    "tags": runnable.tags,
                    "run.results_dir": result_dir,
                },
            ]

            cls._start_logging(runnable.config, queue)

            if "COVERAGE_RUN" in os.environ:
                from coverage import Coverage

                coverage = Coverage()
                coverage.start()

            instance = loader.load_test(test_factory)
            early_state = instance.get_state()
            early_state["type"] = "early_state"
            queue.put(early_state)
            instance.run_avocado()

            if "COVERAGE_RUN" in os.environ:
                coverage.stop()
                coverage.save()

            state = instance.get_state()
            fail_reason = state.get("fail_reason")
            queue.put(messages.WhiteboardMessage.get(state["whiteboard"]))
            queue.put(
                messages.FinishedMessage.get(
                    state["status"].lower(), fail_reason=fail_reason
                )
            )
        except Exception as e:
            queue.put(messages.StderrMessage.get(traceback.format_exc()))
            queue.put(messages.FinishedMessage.get("error", fail_reason=str(e)))

    def run(self, runnable):
        # pylint: disable=W0201
        self.runnable = runnable
        yield messages.StartedMessage.get()
        try:
            queue = multiprocessing.SimpleQueue()
            process = multiprocessing.Process(
                target=self._run_avocado, args=(self.runnable, queue)
            )

            process.start()

            time_started = time.monotonic()

            timeout = float(self.DEFAULT_TIMEOUT)
            most_current_execution_state_time = None
            while True:
                time.sleep(RUNNER_RUN_CHECK_INTERVAL)
                now = time.monotonic()
                if queue.empty():
                    if most_current_execution_state_time is not None:
                        next_execution_state_mark = (
                            most_current_execution_state_time
                            + RUNNER_RUN_STATUS_INTERVAL
                        )
                    if (
                        most_current_execution_state_time is None
                        or now > next_execution_state_mark
                    ):
                        most_current_execution_state_time = now
                        yield messages.RunningMessage.get()
                    if (now - time_started) > timeout:
                        process.terminate()
                        yield messages.FinishedMessage.get("interrupted", "timeout")
                        break
                else:
                    message = queue.get()
                    if message.get("type") == "early_state":
                        timeout = float(message.get("timeout") or self.DEFAULT_TIMEOUT)
                    else:
                        yield message
                    if message.get("status") == "finished":
                        break
        except Exception as e:
            yield messages.StderrMessage.get(traceback.format_exc())
            yield messages.FinishedMessage.get("error", fail_reason=str(e))


class RunnerApp(BaseRunnerApp):
    PROG_NAME = "avocado-runner-avocado-instrumented"
    PROG_DESCRIPTION = "nrunner application for avocado-instrumented tests"
    RUNNABLE_KINDS_CAPABLE = ["avocado-instrumented"]


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == "__main__":
    main()
