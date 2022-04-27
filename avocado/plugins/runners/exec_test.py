import os
import shutil
import subprocess
import tempfile
import time

import pkg_resources

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import (RUNNER_RUN_CHECK_INTERVAL,
                                         RUNNER_RUN_STATUS_INTERVAL,
                                         BaseRunner)


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

    name = 'exec-test'
    description = 'Runner for standalone executables treated as tests'

    CONFIGURATION_USED = ['run.keep_tmp',
                          'runner.exectest.exitcodes.skip']

    def _process_final_status(self, process,
                              stdout=None, stderr=None):  # pylint: disable=W0613
        # Since Runners are standalone, and could be executed on a remote
        # machine in an "isolated" way, there is no way to assume a default
        # value, at this moment.
        skip_codes = self.runnable.config.get('runner.exectest.exitcodes.skip',
                                              [])
        final_status = {}
        if process.returncode in skip_codes:
            final_status['result'] = 'skip'
        elif process.returncode == 0:
            final_status['result'] = 'pass'
        else:
            final_status['result'] = 'fail'

        final_status['returncode'] = process.returncode
        return self.prepare_status('finished', final_status)

    def _cleanup(self):
        """Cleanup method for the exec-test tests"""
        # cleanup temporary directories
        workdir = self.runnable.kwargs.get('AVOCADO_TEST_WORKDIR')
        if (workdir is not None and
                self.runnable.config.get('run.keep_tmp') is not None and
                os.path.exists(workdir)):
            shutil.rmtree(workdir)

    def _create_params(self):
        """Create params for the test"""
        if self.runnable.variant is None:
            return {}

        params = dict([(str(key), str(val)) for _, key, val in
                       self.runnable.variant['variant'][0][1]])
        return params

    @staticmethod
    def _get_avocado_version():
        """Return the Avocado package version, if installed"""
        version = "unknown.unknown"
        try:
            version = pkg_resources.get_distribution(
                'avocado-framework').version
        except pkg_resources.DistributionNotFound:
            pass
        return version

    def _get_env_variables(self):
        """Get the default AVOCADO_* environment variables

        These variables are available to the test environment during the test
        execution.
        """
        # create the temporary work dir
        workdir = tempfile.mkdtemp(prefix='.avocado-workdir-')
        # create the avocado environment variable dictionary
        avocado_test_env_variables = {
            'AVOCADO_VERSION': self._get_avocado_version(),
            'AVOCADO_TEST_WORKDIR': workdir,
        }
        if self.runnable.output_dir:
            avocado_test_env_variables['AVOCADO_TEST_OUTPUTDIR'] = \
                self.runnable.output_dir
        return avocado_test_env_variables

    @staticmethod
    def _is_uri_a_file_on_cwd(uri):
        if (uri is not None and
            os.path.basename(uri) == uri and
                os.access(uri, os.R_OK | os.X_OK)):
            return True
        return False

    def run(self, runnable):
        # pylint: disable=W0201
        self.runnable = runnable

        env = dict(os.environ)
        if self.runnable.kwargs:
            env.update(self.runnable.kwargs)

        # set default Avocado environment variables if running on a valid Task
        if self.runnable.uri is not None:
            avocado_test_env_variables = self._get_env_variables()
            # save environment variables for further cleanup
            self.runnable.kwargs.update(avocado_test_env_variables)
            if env is None:
                env = avocado_test_env_variables
            else:
                env.update(avocado_test_env_variables)

        params = self._create_params()
        if params:
            env.update(params)

        if env and 'PATH' not in env:
            env['PATH'] = os.environ.get('PATH')

        # Support for running executable tests in the current working directory
        if self._is_uri_a_file_on_cwd(self.runnable.uri):
            env['PATH'] += f':{os.getcwd()}'

        try:
            process = subprocess.Popen(
                [self.runnable.uri] + list(self.runnable.args),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env)
        except Exception as e:
            yield self.prepare_status('started')
            yield self.prepare_status('finished', {'result': 'error',
                                                   'fail_reason': str(e)})
            self._cleanup()
            return

        yield self.prepare_status('started')
        most_current_execution_state_time = None
        timeout = RUNNER_RUN_CHECK_INTERVAL
        while process.returncode is None:
            time.sleep(timeout)
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Let's just try again at the next loop
                pass
            now = time.monotonic()
            if most_current_execution_state_time is not None:
                next_execution_state_mark = (most_current_execution_state_time +
                                             RUNNER_RUN_STATUS_INTERVAL)
            if (most_current_execution_state_time is None or
                    now > next_execution_state_mark):
                most_current_execution_state_time = now
                yield self.prepare_status('running')
        yield self.prepare_status('running', {'type': 'stdout', 'log': stdout})
        yield self.prepare_status('running', {'type': 'stderr', 'log': stderr})
        yield self._process_final_status(process, stdout, stderr)
        self._cleanup()


class RunnerApp(BaseRunnerApp):
    PROG_NAME = 'avocado-runner-exec-test'
    PROG_DESCRIPTION = 'nrunner application for exec-test tests'
    RUNNABLE_KINDS_CAPABLE = ['exec-test']


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == '__main__':
    main()
