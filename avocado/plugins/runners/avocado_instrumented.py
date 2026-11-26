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

    PROCESS_JOIN_TIMEOUT = 1.0

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

    @classmethod
    def _start_process(cls, process):
        """Defer parent interruption until start() publishes the child handle."""
        interrupted = False
        parent_pid = os.getpid()

        def defer_interrupt(signum, frame):
            nonlocal interrupted
            if os.getpid() == parent_pid:
                interrupted = True
            else:
                # a forked child must retain its normal signal handling
                cls.signal_handler(signum, frame)

        previous_handler = signal.signal(signal.SIGTERM, defer_interrupt)
        try:
            process.start()
        finally:
            signal.signal(signal.SIGTERM, previous_handler)
        if interrupted:
            cls.signal_handler(signal.SIGTERM, None)

    @classmethod
    def _cleanup_process(cls, process):
        """
        Reap a child eventually terminating it if it outlives the runner.

        Startup failures can leave various partial states and joining
        a partial process is invalid.
        """
        if process is None:
            return
        # repeated termination requests must not interrupt bounded cleanup
        previous_handler = signal.signal(signal.SIGTERM, signal.SIG_IGN)
        try:
            if process.pid is None:
                return
            process.join(cls.PROCESS_JOIN_TIMEOUT)
            if process.is_alive():
                process.terminate()
                process.join(cls.PROCESS_JOIN_TIMEOUT)
            if process.is_alive() and hasattr(process, "kill"):
                process.kill()
                process.join(cls.PROCESS_JOIN_TIMEOUT)
            if not process.is_alive():
                process.close()
        except (AssertionError, OSError, ValueError):
            # cleanup failure must not replace the status already
            # produced by the runner so far
            return
        finally:
            signal.signal(signal.SIGTERM, previous_handler)

    @staticmethod
    def _close_parent_queue_writer(queue):
        """
        Close the parent's unused writer so a dead producer causes EOF.

        Keeping this writer open would prevent the reader from observing
        end-of-stream after the child's writer closes.
        """
        writer = getattr(queue, "_writer", None)
        if writer is not None:
            try:
                writer.close()
            except (OSError, ValueError):
                pass

    @staticmethod
    def _close_queue(queue):
        """
        Close the parent side of a multiprocessing queue.

        The same cleanup path must work after both successful execution
        and incomplete startup.
        """
        close = getattr(queue, "close", None)
        if close is not None:
            try:
                close()
            except (OSError, ValueError):
                pass

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
                try:
                    message = queue.get()
                except EOFError:
                    yield messages.FinishedMessage.get(
                        "error",
                        fail_reason="Instrumented test message queue closed without "
                        "sending a finished message",
                        fail_class="InstrumentedTestMessageQueueError",
                    )
                    return
                if message.get("type") != "early_state":
                    yield message
                if message.get("status") == "finished":
                    break

    def run(self, runnable):
        # pylint: disable=W0201
        signal.signal(signal.SIGTERM, AvocadoInstrumentedTestRunner.signal_handler)
        self.runnable = runnable
        yield messages.StartedMessage.get()
        queue = None
        process = None
        try:
            queue = multiprocessing.SimpleQueue()
            process = multiprocessing.Process(
                target=self._run_avocado, args=(self.runnable, queue)
            )

            self._start_process(process)
            # starting first ensures the child receives its own open
            # writer before the parent closes its copy
            self._close_parent_queue_writer(queue)

            yield from self._monitor(queue)

        except TestInterrupt:
            if process is not None and process.pid is not None:
                self._close_parent_queue_writer(queue)
                if process.is_alive():
                    process.terminate()
                yield from self._monitor(queue)
            else:
                yield messages.FinishedMessage.get(
                    "error",
                    fail_reason="Runner interrupted before the test process started",
                    fail_class="InstrumentedTestProcessError",
                )
        except Exception as e:
            yield messages.StderrMessage.get(traceback.format_exc())
            yield messages.FinishedMessage.get(
                "error",
                fail_reason=str(e),
                fail_class=e.__class__.__name__,
                traceback=traceback.format_exc(),
            )
        finally:
            try:
                self._cleanup_process(process)
            finally:
                self._close_queue(queue)


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
