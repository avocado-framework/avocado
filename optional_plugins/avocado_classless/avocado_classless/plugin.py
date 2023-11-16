#! /usr/bin/python3

# SPDX-License-Identifier: GPL-2.0-or-later
#
# Copyright Red Hat
# Author: David Gibson <david@gibson.dropbear.id.au>

"""
Implementation of the Avocado resolver and runner for classless tests.
"""

import importlib
import multiprocessing
import os.path
import re
import sys
import time
import traceback

from avocado.core.extension_manager import PluginPriority
from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runnable import Runnable
from avocado.core.nrunner.runner import (
    RUNNER_RUN_CHECK_INTERVAL,
    RUNNER_RUN_STATUS_INTERVAL,
    BaseRunner,
)
from avocado.core.plugin_interfaces import Resolver
from avocado.core.resolver import (
    ReferenceResolution,
    ReferenceResolutionResult,
    check_file,
)
from avocado.core.test import Test, TestID
from avocado.core.utils import messages

from .test import MANIFEST

SHBANG = b"#! /usr/bin/env avocado-runner-avocado-classless"
DEFAULT_TIMEOUT = 5.0


def load_mod(path):
    """Load a module containing classless tests"""
    modname = os.path.basename(path)[:-3]
    moddir = os.path.abspath(os.path.dirname(path))

    try:
        sys.path.insert(0, moddir)
        return importlib.import_module(modname)
    finally:
        if moddir in sys.path:
            sys.path.remove(moddir)


class ClasslessResolver(Resolver):
    """Resolver plugin for classless tests"""

    # pylint: disable=R0903

    name = "avocado-classless"
    description = "Resolver for classless tests (not jUnit style)"
    priority = PluginPriority.NORMAL

    def resolve(self, reference):
        if ":" in reference:
            path, pattern = reference.rsplit(":", 1)
        else:
            path, pattern = reference, ""

        # First check it looks like a Python file
        filecheck = check_file(path, reference)
        if filecheck is not True:
            return filecheck

        # Then check it looks like an avocado-classless file
        with open(path, "rb") as testfile:
            shbang = testfile.readline()
        if shbang.strip() != SHBANG:
            return ReferenceResolution(
                reference,
                ReferenceResolutionResult.NOTFOUND,
                info=f'{path} does not have first line "{SHBANG}" line',
            )

        mod = load_mod(path)
        mfest = getattr(mod, MANIFEST)

        pattern = re.compile(pattern)
        runnables = []
        for name in mfest.keys():
            if pattern.search(name):
                runnables.append(Runnable("avocado-classless", f"{path}:{name}"))

        return ReferenceResolution(
            reference,
            ReferenceResolutionResult.SUCCESS,
            runnables,
        )


def run_classless(runnable, queue):
    """Invoked within isolating process, run classless tests"""
    try:
        path, testname = runnable.uri.rsplit(":", 1)
        mod = load_mod(path)
        test = getattr(mod, testname)

        class ClasslessTest(Test):
            """Shim class for classless tests"""

            def test(self):
                """Execute classless test"""
                test()

        result_dir = runnable.output_dir
        instance = ClasslessTest(
            name=TestID(0, runnable.uri),
            config=runnable.config,
            base_logdir=result_dir,
        )

        messages.start_logging(runnable.config, queue)

        instance.run_avocado()

        state = instance.get_state()
        fail_reason = state.get("fail_reason")
        queue.put(
            messages.FinishedMessage.get(
                state["status"].lower(),
                fail_reason=fail_reason,
                fail_class=state.get("fail_class"),
                traceback=state.get("traceback"),
            )
        )
    except Exception as exc:
        queue.put(messages.StderrMessage.get(traceback.format_exc()))
        queue.put(
            messages.FinishedMessage.get(
                "error",
                fail_reason=str(exc),
                fail_class=exc.__class__.__name__,
                traceback=traceback.format_exc(),
            )
        )


class ClasslessRunner(BaseRunner):
    """Runner for classless tests

    When creating the Runnable, use the following attributes:

     * kind: should be 'avocado-classless';

     * uri: path to a test file, then ':' then a function name within that file

     * args: not used;

     * kwargs: not used;

    Example:

       runnable = Runnable(kind='avocado-classless',
                           uri='example.py:test_example')
    """

    name = "avocado-classless"
    description = "Runner for classless tests (not jUnit style)"

    CONFIGURATION_USED = [
        "core.show",
        "job.run.store_logging_stream",
    ]

    def run(self, runnable):
        yield messages.StartedMessage.get()
        try:
            queue = multiprocessing.SimpleQueue()
            process = multiprocessing.Process(
                target=run_classless, args=(runnable, queue)
            )
            process.start()

            time_started = time.monotonic()
            timeout = DEFAULT_TIMEOUT
            next_status_time = None
            while True:
                time.sleep(RUNNER_RUN_CHECK_INTERVAL)
                now = time.monotonic()
                if queue.empty():
                    if next_status_time is None or now > next_status_time:
                        next_status_time = now + RUNNER_RUN_STATUS_INTERVAL
                        yield messages.RunningMessage.get()
                    if (now - time_started) > timeout:
                        process.terminate()
                        yield messages.FinishedMessage.get("interrupted", "timeout")
                        break
                else:
                    message = queue.get()
                    yield message
                    if message.get("status") == "finished":
                        break
        except Exception as exc:
            yield messages.StderrMessage.get(traceback.format_exc())
            yield messages.FinishedMessage.get(
                "error",
                fail_reason=str(exc),
                fail_class=exc.__class__.__name__,
                traceback=traceback.format_exc(),
            )


class RunnerApp(BaseRunnerApp):
    """Runner app for classless tests"""

    PROG_NAME = "avocado-runner-avocado-classless"
    PROG_DESCRIPTION = "nrunner application for classless tests"
    RUNNABLE_KINDS_CAPABLE = ["avocado-classless"]


def main():
    """Run some avocado-classless tests"""
    app = RunnerApp(print)
    app.run()


if __name__ == "__main__":
    main()
