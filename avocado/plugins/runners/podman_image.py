import asyncio
import logging
import sys
from multiprocessing import set_start_method

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import PythonBaseRunner
from avocado.core.utils import messages
from avocado.utils.podman import AsyncPodman, PodmanException


class PodmanImageRunner(PythonBaseRunner):
    """Runner for dependencies of type podman-image

    This runner handles download and verification.

    Runnable attributes usage:

     * kind: 'podman-image'

     * uri: the name of the image

     * args: not used
    """

    name = "podman-image"
    description = f"Runner for dependencies of type {name}"

    def _run(self, runnable, queue):
        # Silence the podman utility from outputting messages into
        # the regular handler, which will go to stdout.  The
        # exceptions caught here still contain all the needed
        # information for debugging in case of errors.
        if not runnable.uri:
            reason = "uri identifying the podman image is required"
            queue.put(messages.FinishedMessage.get("error", reason))
        else:
            logging.getLogger("avocado.utils.podman").addHandler(logging.NullHandler())
            try:
                podman = AsyncPodman()
                loop = asyncio.get_event_loop()
                loop.run_until_complete(podman.execute("pull", runnable.uri))
                queue.put(messages.FinishedMessage.get(result="pass"))
            except PodmanException as ex:
                queue.put(
                    messages.FinishedMessage.get(
                        result="fail", fail_reason=f"Could not pull podman image: {ex}"
                    )
                )


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
