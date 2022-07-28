import os
import shutil
import subprocess
import tempfile

import pkg_resources

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import BaseRunner


class ExecTestRunner(BaseRunner):
    """
    Runner for standalone executables treated as tests

    This is similar in concept to the Avocado "SIMPLE" test type, in which an
    executable returning 0 means that a test passed, and anything else means
    that a test failed.

    Runnable attributes usage:

     * uri: path to a binary to be executed as another process

     * args: arguments to be given on the command line to the
       binary given by path

     * kwargs: key=val to be set as environment variables to the
       process
    """

    name = "exec-test"
    description = "Runner for standalone executables treated as tests"

    CONFIGURATION_USED = ["run.keep_tmp", "runner.exectest.exitcodes.skip"]

    def _process_final_status(
        self, process, runnable, stdout=None, stderr=None
    ):  # pylint: disable=W0613
        # Since Runners are standalone, and could be executed on a remote
        # machine in an "isolated" way, there is no way to assume a default
        # value, at this moment.
        skip_codes = runnable.config.get("runner.exectest.exitcodes.skip", [])
        final_status = {}
        if skip_codes is None:
            skip_codes = []
        if process.returncode in skip_codes:
            final_status["result"] = "skip"
        elif process.returncode == 0:
            final_status["result"] = "pass"
        else:
            final_status["result"] = "fail"

        final_status["returncode"] = process.returncode
        return self.prepare_status("finished", final_status)

    def _cleanup(self, runnable):
        """Cleanup method for the exec-test tests"""
        # cleanup temporary directories
        workdir = runnable.kwargs.get("AVOCADO_TEST_WORKDIR")
        if (
            workdir is not None
            and runnable.config.get("run.keep_tmp") is not None
            and os.path.exists(workdir)
        ):
            shutil.rmtree(workdir)

    def _create_params(self, runnable):
        """Create params for the test"""
        if runnable.variant is None:
            return {}

        params = dict(
            [(str(key), str(val)) for _, key, val in runnable.variant["variant"][0][1]]
        )
        return params

    @staticmethod
    def _get_avocado_version():
        """Return the Avocado package version, if installed"""
        version = "unknown.unknown"
        try:
            version = pkg_resources.get_distribution("avocado-framework").version
        except pkg_resources.DistributionNotFound:
            pass
        return version

    def _get_env_variables(self, runnable):
        """Get the default AVOCADO_* environment variables

        These variables are available to the test environment during the test
        execution.
        """
        # create the temporary work dir
        workdir = tempfile.mkdtemp(prefix=".avocado-workdir-")
        # create the avocado environment variable dictionary
        avocado_test_env_variables = {
            "AVOCADO_VERSION": self._get_avocado_version(),
            "AVOCADO_TEST_WORKDIR": workdir,
        }
        if runnable.output_dir:
            avocado_test_env_variables["AVOCADO_TEST_OUTPUTDIR"] = runnable.output_dir
        return avocado_test_env_variables

    @staticmethod
    def _is_uri_a_file_on_cwd(uri):
        if (
            uri is not None
            and os.path.basename(uri) == uri
            and os.access(uri, os.R_OK | os.X_OK)
        ):
            return True
        return False

    def _get_env(self, runnable):
        env = dict(os.environ)
        if runnable.kwargs:
            env.update(runnable.kwargs)

        # set default Avocado environment variables if running on a valid Task
        if runnable.uri is not None:
            avocado_test_env_variables = self._get_env_variables(runnable)
            # save environment variables for further cleanup
            runnable.kwargs.update(avocado_test_env_variables)
            if env is None:
                env = avocado_test_env_variables
            else:
                env.update(avocado_test_env_variables)

        params = self._create_params(runnable)
        if params:
            env.update(params)

        if env and "PATH" not in env:
            env["PATH"] = os.environ.get("PATH")

        # Support for running executable tests in the current working directory
        if self._is_uri_a_file_on_cwd(runnable.uri):
            env["PATH"] += f":{os.getcwd()}"

        return env

    def _run_proc(self, runnable):
        return subprocess.Popen(
            [runnable.uri] + list(runnable.args),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self._get_env(runnable),
        )

    def run(self, runnable):
        yield self.prepare_status("started")

        try:
            process = self._run_proc(runnable)
        except Exception as e:
            yield self.prepare_status(
                "finished", {"result": "error", "fail_reason": str(e)}
            )
            self._cleanup(runnable)
            return

        def poll_proc():
            return process.poll() is not None

        yield from self.running_loop(poll_proc)

        stdout = process.stdout.read()
        stderr = process.stderr.read()

        yield self.prepare_status("running", {"type": "stdout", "log": stdout})
        yield self.prepare_status("running", {"type": "stderr", "log": stderr})
        yield self._process_final_status(process, runnable, stdout, stderr)
        self._cleanup(runnable)


class RunnerApp(BaseRunnerApp):
    PROG_NAME = "avocado-runner-exec-test"
    PROG_DESCRIPTION = "nrunner application for exec-test tests"
    RUNNABLE_KINDS_CAPABLE = ["exec-test"]


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == "__main__":
    main()
