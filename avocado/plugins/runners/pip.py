import sys
from multiprocessing import set_start_method

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import BaseRunner
from avocado.core.utils import messages
from avocado.utils import process


class PipRunnerError(Exception):
    """
    Generic error for PipRunner.
    """


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

    def _run(self, runnable):
        # check if there is a valid 'action' argument
        cmd = runnable.kwargs.get("action", "install")
        # avoid invalid arguments
        if cmd not in ["install", "uninstall"]:
            raise PipRunnerError(
                f"Invalid action {cmd}. Use one of 'install' or 'remove'"
            )

        package = runnable.kwargs.get("name")
        # if package was passed correctly, run python -m pip
        if package is not None:
            cmd = f"python3 -m ensurepip && python3 -m pip {cmd} {package}"
            result = process.run(cmd, shell=True)
        yield messages.StdoutMessage.get(result.stdout)
        yield messages.StderrMessage.get(result.stderr)
        yield messages.FinishedMessage.get("pass")


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
