import multiprocessing
import os
import sys
import tempfile

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import BaseRunner
from avocado.core.test import TestID
from avocado.core.tree import TreeNodeEnvOnly
from avocado.core.utils import loader, messages
from avocado.core.varianter import is_empty_variant


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

    def _run(self, runnable):
        def load_and_run_test(test_factory):
            instance = loader.load_test(test_factory)
            instance.run_avocado()
            return instance.get_state()

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
        yield messages.WhiteboardMessage.get(state["whiteboard"])
        yield messages.FinishedMessage.get(
            state["status"].lower(),
            fail_reason=fail_reason,
            class_name=klass,
            fail_class=state.get("fail_class"),
            traceback=state.get("traceback"),
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
