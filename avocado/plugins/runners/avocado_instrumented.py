import multiprocessing
import os
import signal
import sys
import tempfile
import time
import traceback

from avocado.core.exceptions import TestInterrupt
from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import RUNNER_RUN_CHECK_INTERVAL, BaseRunner
from avocado.core.test import TestID
from avocado.core.tree import TreeNodeEnvOnly
from avocado.core.utils import loader, messages
from avocado.core.varianter import is_empty_variant
from avocado.utils.deprecation import log_deprecation


class AvocadoInstrumentedTestRunner(BaseRunner):
    """
    Runner for avocado-instrumented tests

    Runnable attributes usage:

     * uri: path to a test file, combined with an Avocado.Test
       inherited class name and method.  The test file path and
       class and method names should be separated by a ":".  One
       example of a valid uri is "mytest.py:Class.test_method".

     * args: not used
    """

    name = "avocado-instrumented"
    description = "Runner for avocado-instrumented tests"

    CONFIGURATION_USED = [
        "run.test_parameters",
        "datadir.paths.cache_dirs",
        "core.show",
        "job.output.loglevel",
        "job.run.store_logging_stream",
    ]

    @staticmethod
    def signal_handler(signum, frame):  # pylint: disable=W0613
        if signum == signal.SIGTERM.value:
            raise TestInterrupt("Test interrupted: Timeout reached")

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
    def _run_avocado(runnable, queue):
        def load_and_run_test(test_factory):
            instance = loader.load_test(test_factory)
            early_state = instance.get_state()
            early_state["type"] = "early_state"
            queue.put(early_state)
            log_deprecation.flush()
            instance.run_avocado()
            return instance.get_state()

        try:
            # This assumes that a proper resolution (see resolver module)
            # was performed, and that a URI contains:
            # 1) path to python module
            # 2) class
            # 3) method
            #
            # To be defined: if the resolution uri should be composed like
            # this, or broken down and stored into other data fields
            signal.signal(signal.SIGTERM, AvocadoInstrumentedTestRunner.signal_handler)
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

            messages.start_logging(runnable.config, queue)

            # running the actual test
            if "COVERAGE_RUN" in os.environ:
                from coverage import Coverage

                coverage = Coverage(data_suffix=True)
                with coverage.collect():
                    state = load_and_run_test(test_factory)
                coverage.save()
            else:
                state = load_and_run_test(test_factory)

            fail_reason = state.get("fail_reason")
            queue.put(messages.WhiteboardMessage.get(state["whiteboard"]))
            queue.put(
                messages.FinishedMessage.get(
                    state["status"].lower(),
                    fail_reason=fail_reason,
                    class_name=klass,
                    fail_class=state.get("fail_class"),
                    traceback=state.get("traceback"),
                )
            )
        except Exception as e:
            queue.put(messages.StderrMessage.get(traceback.format_exc()))
            queue.put(
                messages.FinishedMessage.get(
                    "error",
                    fail_reason=str(e),
                    fail_class=e.__class__.__name__,
                    traceback=traceback.format_exc(),
                )
            )

    @staticmethod
    def _monitor(queue):
        while True:
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)
            if queue.empty():
                yield messages.RunningMessage.get()
            else:
                message = queue.get()
                if message.get("type") != "early_state":
                    yield message
                if message.get("status") == "finished":
                    break

    def run(self, runnable):
        # pylint: disable=W0201
        signal.signal(signal.SIGTERM, AvocadoInstrumentedTestRunner.signal_handler)
        self.runnable = runnable
        yield messages.StartedMessage.get()
        try:
            queue = multiprocessing.SimpleQueue()
            process = multiprocessing.Process(
                target=self._run_avocado, args=(self.runnable, queue)
            )

            process.start()

            yield from self._monitor(queue)

        except TestInterrupt:
            process.terminate()
            yield from self._monitor(queue)
        except Exception as e:
            yield messages.StderrMessage.get(traceback.format_exc())
            yield messages.FinishedMessage.get(
                "error",
                fail_reason=str(e),
                fail_class=e.__class__.__name__,
                traceback=traceback.format_exc(),
            )


class RunnerApp(BaseRunnerApp):
    PROG_NAME = "avocado-runner-avocado-instrumented"
    PROG_DESCRIPTION = "nrunner application for avocado-instrumented tests"
    RUNNABLE_KINDS_CAPABLE = ["avocado-instrumented"]


def main():
    if sys.platform == "darwin":
        multiprocessing.set_start_method("fork")
    app = RunnerApp(print)
    app.run()


if __name__ == "__main__":
    main()
