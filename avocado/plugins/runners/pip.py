import sys
import traceback
from multiprocessing import set_start_method

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import BaseRunner
from avocado.core.utils import messages
from avocado.utils import process


class PipRunner(BaseRunner):
    """Runner for dependencies of type pip

    This runner handles, the installation, verification and removal of
    packages using the pip.

    Runnable attributes usage:

     * kind: 'pip'

     * uri: not used

     * args: not used

     * kwargs:
        - name: the package name (required)
        - action: one of 'install' or 'uninstall' (optional, defaults
          to 'install')
    """

    name = "pip"
    description = "Runner for dependencies of type pip"

    def run(self, runnable):
        try:
            yield messages.StartedMessage.get()
            # check if there is a valid 'action' argument
            cmd = runnable.kwargs.get("action", "install")
            # avoid invalid arguments
            if cmd not in ["install", "uninstall"]:
                stderr = f"Invalid action {cmd}. Use one of 'install' or 'remove'"
                yield messages.StderrMessage.get(stderr.encode())
                yield messages.FinishedMessage.get("error")
                return

            package = runnable.kwargs.get("name")
            # if package was passed correctly, run python -m pip
            result = None
            if package is not None:
                try:
                    cmd = f"python3 -m ensurepip && python3 -m pip {cmd} {package}"
                    result = process.run(cmd, shell=True)
                except Exception as e:
                    yield messages.StderrMessage.get(str(e))
                    yield messages.FinishedMessage.get("error")
                    return

            if result is not None:
                yield messages.StdoutMessage.get(result.stdout)
                yield messages.StderrMessage.get(result.stderr)
                yield messages.FinishedMessage.get("pass")
            else:
                yield messages.StderrMessage.get("Package name is required")
                yield messages.FinishedMessage.get("error")
        except Exception as e:
            yield messages.StderrMessage.get(traceback.format_exc())
            yield messages.FinishedMessage.get(
                "error",
                fail_reason=str(e),
                fail_class=e.__class__.__name__,
                traceback=traceback.format_exc(),
            )


class RunnerApp(BaseRunnerApp):
    PROG_NAME = "avocado-runner-pip"
    PROG_DESCRIPTION = "nrunner application for dependencies of type pip"
    RUNNABLE_KINDS_CAPABLE = ["pip"]


def main():
    if sys.platform == "darwin":
        set_start_method("fork")
    app = RunnerApp(print)
    app.run()


if __name__ == "__main__":
    main()
