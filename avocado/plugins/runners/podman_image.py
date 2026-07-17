import asyncio
import logging
import sys
import time
from multiprocessing import Process, SimpleQueue, set_start_method

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import RUNNER_RUN_STATUS_INTERVAL, BaseRunner
from avocado.core.utils import messages
from avocado.utils.podman import AsyncPodman, PodmanException


class PodmanImageRunner(BaseRunner):
    """Runner for dependencies of type podman-image

    This runner handles download and verification.

    Runnable attributes usage:

     * kind: 'podman-image'

     * uri: the name of the image

     * args: not used
    """

    name = "podman-image"
    description = f"Runner for dependencies of type {name}"

    def _run_podman_pull(self, uri, queue):
        # Silence the podman utility from outputting messages into
        # the regular handler, which will go to stdout.  The
        # exceptions caught here still contain all the needed
        # information for debugging in case of errors.
        logging.getLogger("avocado.utils.podman").addHandler(logging.NullHandler())
        try:
            podman = AsyncPodman()
            asyncio.run(podman.execute("pull", uri))
            queue.put({"result": "pass"})
        except PodmanException as ex:
            queue.put(
                {"result": "fail", "fail_reason": f"Could not pull podman image: {ex}"}
            )
        except Exception as ex:  # pylint: disable=broad-except
            queue.put(
                {
                    "result": "error",
                    "fail_reason": f"Could not run podman image process: {ex}",
                    "fail_class": ex.__class__.__name__,
                }
            )

    def run(self, runnable):
        yield messages.StartedMessage.get()

        if not runnable.uri:
            reason = "uri identifying the podman image is required"
            yield messages.FinishedMessage.get("error", reason)
        else:
            queue = SimpleQueue()
            process = Process(target=self._run_podman_pull, args=(runnable.uri, queue))
            try:
                process.start()
            except Exception as ex:  # pylint: disable=broad-except
                yield messages.FinishedMessage.get(
                    "error",
                    fail_reason=f"Could not start podman image process: {ex}",
                    fail_class=ex.__class__.__name__,
                )
                return
            while queue.empty():
                if not process.is_alive():
                    process.join()
                    if queue.empty():
                        yield messages.FinishedMessage.get(
                            "error",
                            fail_reason=(
                                "Podman image process exited with status "
                                f"{process.exitcode} without reporting a result"
                            ),
                        )
                        return
                    break
                time.sleep(RUNNER_RUN_STATUS_INTERVAL)
                yield messages.RunningMessage.get()

            output = queue.get()
            process.join()
            result = output.pop("result")
            yield messages.FinishedMessage.get(result, **output)


class RunnerApp(BaseRunnerApp):
    PROG_NAME = f"avocado-runner-{PodmanImageRunner.name}"
    PROG_DESCRIPTION = PodmanImageRunner.description
    RUNNABLE_KINDS_CAPABLE = [PodmanImageRunner.name]


def main():
    if sys.platform == "darwin":
        set_start_method("fork")
    app = RunnerApp(print)
    app.run()


if __name__ == "__main__":
    main()
