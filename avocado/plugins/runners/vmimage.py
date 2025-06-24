import multiprocessing
import sys
from multiprocessing import set_start_method

from avocado.core.exceptions import TestInterrupt
from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import BaseRunner
from avocado.core.utils import messages
from avocado.plugins.vmimage import download_image
from avocado.utils import vmimage


class VMImageRunnerError(Exception):
    """
    Generic error for VMImageRunner.
    """


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

    def _run(self, runnable):
        try:
            # Get parameters from runnable.kwargs
            provider = runnable.kwargs.get("provider")
            version = runnable.kwargs.get("version")
            arch = runnable.kwargs.get("arch")

            if not provider:
                raise VMImageRunnerError("Missing required parameter: provider")

            message = f"Getting VM image for {provider}"
            if version:
                message += f" {version}"
            if arch:
                message += f" {arch}"
            yield messages.StdoutMessage.get(message.encode())

            yield messages.StdoutMessage.get(
                f"Attempting to download image for {provider} (version: {version or 'latest'}, arch: {arch})".encode()
            )

            image = download_image(provider, version, arch)
            if not image:
                raise VMImageRunnerError("Failed to get image")

            yield messages.StdoutMessage.get(
                f"Successfully retrieved VM image from cache or downloaded to: {image['file']}".encode()
            )
            yield messages.FinishedMessage.get("pass")

        except (AttributeError, RuntimeError, vmimage.ImageProviderError) as e:
            # AttributeError: provider not found
            # RuntimeError: failed to get image
            # ImageProviderError: provider-specific errors
            raise VMImageRunnerError(f"Failed to download image: {str(e)}".encode())
        except (TestInterrupt, multiprocessing.TimeoutError) as e:
            raise VMImageRunnerError(f"Operation interrupted: {str(e)}".encode())


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
