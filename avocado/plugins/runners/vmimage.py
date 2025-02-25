import multiprocessing
import signal
import sys
import time
import traceback
from multiprocessing import set_start_method

from avocado.core.exceptions import TestInterrupt
from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import RUNNER_RUN_CHECK_INTERVAL, BaseRunner
from avocado.core.utils import messages
from avocado.core.utils.messages import start_logging
from avocado.plugins.vmimage import download_image
from avocado.utils import vmimage


class VMImageRunner(BaseRunner):
    """
    Runner for dependencies of type vmimage.
    This runner uses the vmimage plugin's download_image function which handles:
    1. Checking if the image exists in cache
    2. Downloading the image if not in cache
    3. Storing the image in the configured cache directory
    4. Returning the cached image path
    """

    name = "vmimage"
    description = "Runner for dependencies of type vmimage"

    @staticmethod
    def signal_handler(signum, frame):  # pylint: disable=W0613
        if signum == signal.SIGTERM.value:
            raise TestInterrupt("VM image operation interrupted: Timeout reached")

    @staticmethod
    def _run_vmimage_operation(runnable, queue):
        try:
            signal.signal(signal.SIGTERM, VMImageRunner.signal_handler)
            start_logging(runnable.config, queue)
            provider = runnable.kwargs.get("provider")
            version = runnable.kwargs.get("version")
            arch = runnable.kwargs.get("arch")

            if not all([provider, version, arch]):
                stderr = "Missing required parameters: provider, version, and arch"
                queue.put(messages.StderrMessage.get(stderr.encode()))
                queue.put(messages.FinishedMessage.get("error"))
                return

            queue.put(
                messages.StdoutMessage.get(
                    f"Getting VM image for {provider} {version} {arch}".encode()
                )
            )

            try:
                # download_image will use cache if available, otherwise download
                # It will raise AttributeError if provider is not found
                provider_normalized = provider.lower()
                image = download_image(provider_normalized, version, arch)
                if not image:
                    raise RuntimeError("Failed to get image")

                queue.put(
                    messages.StdoutMessage.get(
                        f"Successfully retrieved VM image from cache or downloaded to: {image['file']}".encode()
                    )
                )
                queue.put(messages.FinishedMessage.get("pass"))

            except (AttributeError, RuntimeError, vmimage.ImageProviderError) as e:
                # AttributeError: provider not found
                # RuntimeError: failed to get image
                # ImageProviderError: provider-specific errors
                queue.put(
                    messages.StderrMessage.get(
                        f"Failed to download image: {str(e)}".encode()
                    )
                )
                queue.put(
                    messages.FinishedMessage.get(
                        "error",
                        fail_reason=str(e),
                        fail_class=e.__class__.__name__,
                        traceback=traceback.format_exc(),
                    )
                )

        except (TestInterrupt, multiprocessing.TimeoutError) as e:
            queue.put(messages.StderrMessage.get(traceback.format_exc().encode()))
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
                yield message
                if message.get("status") == "finished":
                    break

    def run(self, runnable):
        signal.signal(signal.SIGTERM, VMImageRunner.signal_handler)
        yield messages.StartedMessage.get()
        try:
            queue = multiprocessing.SimpleQueue()
            process = multiprocessing.Process(
                target=self._run_vmimage_operation, args=(runnable, queue)
            )

            process.start()

            for message in self._monitor(queue):
                yield message

        except TestInterrupt:
            process.terminate()
            for message in self._monitor(queue):
                yield message
        except (multiprocessing.ProcessError, OSError) as e:
            # ProcessError: Issues with process management
            # OSError: System-level errors (e.g. resource limits)
            yield messages.StderrMessage.get(traceback.format_exc().encode())
            yield messages.FinishedMessage.get(
                "error",
                fail_reason=str(e),
                fail_class=e.__class__.__name__,
                traceback=traceback.format_exc(),
            )


class RunnerApp(BaseRunnerApp):
    PROG_NAME = "avocado-runner-vmimage"
    PROG_DESCRIPTION = "nrunner application for dependencies of type vmimage"
    RUNNABLE_KINDS_CAPABLE = ["vmimage"]


def main():
    if sys.platform == "darwin":
        set_start_method("fork")
    app = RunnerApp(print)
    app.run()


if __name__ == "__main__":
    main()
