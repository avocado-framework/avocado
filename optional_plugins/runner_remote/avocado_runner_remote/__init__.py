# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2014-2017
# Authors: Ruda Moura <rmoura@redhat.com>
#          Cleber Rosa <crosa@redhat.com>

import getpass
import json
import logging
import os
import re
import sys
import time

import fabric.api
import fabric.network
import fabric.operations
import fabric.tasks
from fabric.context_managers import shell_env
from fabric.exceptions import CommandTimeout

from avocado.core import exceptions
from avocado.core import exit_codes
from avocado.core import loader
from avocado.core import output
from avocado.core import status
from avocado.core.output import LOG_JOB, LOG_UI
from avocado.core.plugin_interfaces import CLI
from avocado.core.runner import TestRunner
from avocado.core.settings import settings
from avocado.core.test import TestName
from avocado.utils import archive
from avocado.utils import astring
from avocado.utils import process
from avocado.utils import stacktrace


class RemoterError(Exception):
    pass


class ConnectionError(RemoterError):
    pass


def _get_env_vars(env_vars):
    """
    Gets environment variables.

    :param variables: A list of variables to get.
    :return: A dictionary with variables names and values.
    """
    env_vars_map = {}
    for var in env_vars:
        value = os.environ.get(var)
        if value is not None:
            env_vars_map[var] = value
    return env_vars_map


def run(command, ignore_status=False, quiet=True, timeout=60):
    """
    Executes a command on the defined fabric hosts.

    This is basically a wrapper to fabric.operations.run, encapsulating
    the result on an avocado process.CmdResult object. This also assumes
    the fabric environment was previously (and properly) initialized.

    :param command: the command string to execute.
    :param ignore_status: Whether to not raise exceptions in case the
        command's return code is different than zero.
    :param timeout: Maximum time allowed for the command to return.
    :param quiet: Whether to not log command stdout/err. Default: True.

    :return: the result of the remote program's execution.
    :rtype: :class:`avocado.utils.process.CmdResult`.
    :raise fabric.exceptions.CommandTimeout: When timeout exhausted.
    """

    result = process.CmdResult()
    start_time = time.time()
    end_time = time.time() + (timeout or 0)   # Support timeout=None
    # Fabric sometimes returns NetworkError even when timeout not reached
    fabric_result = None
    fabric_exception = None
    while True:
        try:
            fabric_result = fabric.operations.run(command=command,
                                                  quiet=quiet,
                                                  warn_only=True,
                                                  timeout=timeout,
                                                  pty=False,
                                                  combine_stderr=False)
            break
        except fabric.network.NetworkError as details:
            fabric_exception = details
            timeout = end_time - time.time()
        if time.time() < end_time:
            break
    if fabric_result is None:
        if fabric_exception is not None:
            raise fabric_exception  # it's not None pylint: disable=E0702
        else:
            raise fabric.network.NetworkError("Remote execution of '%s'"
                                              "failed without any "
                                              "exception. This should not "
                                              "happen." % command)
    end_time = time.time()
    duration = end_time - start_time
    result.command = command
    result.stdout = str(fabric_result.stdout)
    result.stderr = str(fabric_result.stderr)
    result.duration = duration
    result.exit_status = fabric_result.return_code
    result.failed = fabric_result.failed
    result.succeeded = fabric_result.succeeded
    if not ignore_status:
        if result.failed:
            raise process.CmdError(command=command, result=result)
    return result


def send_files(local_path, remote_path):
    """
    Send files to the defined fabric host.

    This assumes the fabric environment was previously (and properly)
    initialized.

    :param local_path: the local path.
    :param remote_path: the remote path.
    """
    try:
        fabric.operations.put(local_path, remote_path,
                              mirror_local_mode=True)
    except ValueError:
        return False
    return True


def receive_files(local_path, remote_path):
    """
    Receive files from the defined fabric host.

    This assumes the fabric environment was previously (and properly)
    initialized.

    :param local_path: the local path.
    :param remote_path: the remote path.
    """
    try:
        fabric.operations.get(remote_path,
                              local_path)
    except ValueError:
        return False
    return True


def _update_fabric_env(method):
    """
    Update fabric env with the appropriate parameters.

    :param method: Remote method to wrap.
    :return: Wrapped method.
    """
    def wrapper(*args, **kwargs):
        fabric.api.env.update(host_string=args[0].hostname,
                              user=args[0].username,
                              key_filename=args[0].key_filename,
                              password=args[0].password,
                              port=args[0].port)
        return method(*args, **kwargs)
    return wrapper


class Remote(object):

    """
    Performs remote operations.
    """

    def __init__(self, hostname, username=None, password=None,
                 key_filename=None, port=22, timeout=60, attempts=10,
                 env_keep=None):
        """
        Creates an instance of :class:`Remote`.

        :param hostname: the hostname.
        :param username: the username. Default: autodetect.
        :param password: the password. Default: try to use public key.
        :param key_filename: path to an identity file (Example: .pem files
            from Amazon EC2).
        :param timeout: remote command timeout, in seconds. Default: 60.
        :param attempts: number of attempts to connect. Default: 10.
        """
        self.hostname = hostname
        if username is None:
            username = getpass.getuser()
        self.username = username
        self.key_filename = key_filename
        # None = use public key
        self.password = password
        self.port = port
        reject_unknown_hosts = settings.get_value('remoter.behavior',
                                                  'reject_unknown_hosts',
                                                  key_type=bool,
                                                  default=False)
        disable_known_hosts = settings.get_value('remoter.behavior',
                                                 'disable_known_hosts',
                                                 key_type=bool,
                                                 default=False)
        if env_keep is None:
            self.env_vars = {}
        else:
            self.env_vars = _get_env_vars(env_keep)
        fabric.api.env.update(host_string=hostname,
                              user=username,
                              password=password,
                              key_filename=key_filename,
                              port=port,
                              timeout=timeout / attempts,
                              connection_attempts=attempts,
                              linewise=True,
                              abort_on_prompts=True,
                              abort_exception=ConnectionError,
                              reject_unknown_hosts=reject_unknown_hosts,
                              disable_known_hosts=disable_known_hosts)

    @_update_fabric_env
    def run(self, command, ignore_status=False, quiet=True, timeout=60):
        """
        Run a command on the remote host.

        :param command: the command string to execute.
        :param ignore_status: Whether to not raise exceptions in case the
            command's return code is different than zero.
        :param timeout: Maximum time allowed for the command to return.
        :param quiet: Whether to not log command stdout/err. Default: True.

        :return: the result of the remote program's execution.
        :rtype: :class:`avocado.utils.process.CmdResult`.
        :raise fabric.exceptions.CommandTimeout: When timeout exhausted.
        """

        with shell_env(**self.env_vars):    # pylint: disable=E1129
            return_dict = fabric.tasks.execute(run, command, ignore_status,
                                               quiet, timeout,
                                               hosts=[self.hostname])
            return return_dict[self.hostname]

    def uptime(self):
        """
        Performs uptime (good to check connection).

        :return: the uptime string or empty string if fails.
        """
        res = self.run('uptime', ignore_status=True)
        if res.exit_status == 0:
            return res
        else:
            return ''

    def makedir(self, remote_path):
        """
        Create a directory.

        :param remote_path: the remote path to create.
        """
        self.run('mkdir -p %s' % remote_path)

    @_update_fabric_env
    def send_files(self, local_path, remote_path):
        """
        Send files to remote host.

        :param local_path: the local path.
        :param remote_path: the remote path.
        """
        result_dict = fabric.tasks.execute(send_files, local_path,
                                           remote_path, hosts=[self.hostname])
        return result_dict[self.hostname]

    @_update_fabric_env
    def receive_files(self, local_path, remote_path):
        """
        Receive files from the remote host.

        :param local_path: the local path.
        :param remote_path: the remote path.
        """
        result_dict = fabric.tasks.execute(receive_files, local_path,
                                           remote_path, hosts=[self.hostname])
        return result_dict[self.hostname]


class RemoteTestRunner(TestRunner):

    """ Tooled TestRunner to run on remote machine using ssh """

    # Let's use re.MULTILINE because sometimes servers might have MOTD
    # that will introduce a line break on output.
    remote_version_re = re.compile(r'^Avocado (\d+)\.(\d+)\r?$',
                                   re.MULTILINE)

    def __init__(self, job, result):
        super(RemoteTestRunner, self).__init__(job, result)
        #: remoter connection to the remote machine
        self.remote = None

    def setup(self):
        """ Setup remote environment and copy test directories """
        stdout_claimed_by = getattr(self.job.args, 'stdout_claimed_by', None)
        if not stdout_claimed_by:
            self.job.log.info("LOGIN      : %s@%s:%d (TIMEOUT: %s seconds)",
                              self.job.args.remote_username,
                              self.job.args.remote_hostname,
                              self.job.args.remote_port,
                              self.job.args.remote_timeout)
        self.remote = Remote(hostname=self.job.args.remote_hostname,
                             username=self.job.args.remote_username,
                             password=self.job.args.remote_password,
                             key_filename=self.job.args.remote_key_file,
                             port=self.job.args.remote_port,
                             timeout=self.job.args.remote_timeout,
                             env_keep=self.job.args.env_keep)

    def check_remote_avocado(self):
        """
        Checks if the remote system appears to have avocado installed

        The "appears to have" description is justified by the fact that the
        check is rather simplistic, it attempts to run an `avocado -v` command
        and checks if the output looks like what avocado would print out.

        :rtype: tuple with (bool, tuple)
        :returns: (True, (x, y, z)) if avocado appears to be installed and
                  (False, None) otherwise.
        """
        # This will be useful as extra debugging info in case avocado
        # doesn't seem to be available in the remote system.
        self.remote.run('env', ignore_status=True, timeout=60)

        result = self.remote.run('avocado -v',
                                 ignore_status=True,
                                 timeout=60)
        if result.exit_status == 127:
            return (False, None)

        match = self.remote_version_re.findall(result.stderr)
        if match is None:
            return (False, None)

        try:
            return (True, tuple(int(_) for _ in match[0]))
        except IndexError:
            return (False, None)

    @staticmethod
    def _parse_json_response(json_output):
        """
        Try to parse JSON response from the remote output.

        It tries to find start of the json dictionary and then grabs
        everything till the end of the dictionary. It supports single-
        line as well as multi-line pretty json output.
        """
        _result = iter(json_output.splitlines())
        json_result = ""
        response = None
        for line in _result:    # Find the beginning
            if line.startswith('{'):
                json_result += line
                break
        else:
            raise ValueError("Could not find the beginning of the remote JSON"
                             " output:\n%s" % output)
        if json_result.endswith('}'):   # probably single-line
            try:
                response = json.loads(json_result)
            except ValueError:
                pass
        if not response:
            # Json was incomplete, try to find another end
            for line in _result:
                json_result += line
                if line.startswith('}'):
                    try:
                        response = json.loads(json_result)
                        break
                    except ValueError:
                        pass
        if not response:
            raise ValueError("Could not find the end of the remote JSON "
                             "output:\n%s" % output)
        return response

    def run_test(self, references, timeout):
        """
        Run tests.

        :param references: a string with test references.
        :return: a dictionary with test results.
        """
        extra_params = []
        mux_files = getattr(self.job.args, 'mux_yaml') or []
        if mux_files:
            extra_params.append("-m %s" % " ".join(mux_files))

        if getattr(self.job.args, "dry_run", False):
            extra_params.append("--dry-run")
        references_str = " ".join(references)

        avocado_cmd = ('avocado run --force-job-id %s --json - '
                       '--archive %s %s' % (self.job.unique_id,
                                            references_str, " ".join(extra_params)))
        try:
            result = self.remote.run(avocado_cmd, ignore_status=True,
                                     timeout=timeout)
            if result.exit_status & exit_codes.AVOCADO_JOB_FAIL:
                raise exceptions.JobError("Remote execution failed with: %s" % result.stderr)

        except CommandTimeout:
            raise exceptions.JobError("Remote execution took longer than "
                                      "specified timeout (%s). Interrupting."
                                      % (timeout))

        try:
            json_result = self._parse_json_response(result.stdout)
        except:
            stacktrace.log_exc_info(sys.exc_info(), logger='avocado.debug')
            raise exceptions.JobError(result.stdout)

        for t_dict in json_result['tests']:
            logdir = os.path.join(self.job.logdir, 'test-results')
            relative_path = astring.string_to_safe_path(t_dict['test'])
            logdir = os.path.join(logdir, relative_path)
            t_dict['logdir'] = logdir
            t_dict['logfile'] = os.path.join(logdir, 'debug.log')

        return json_result

    def run_suite(self, test_suite, variants, timeout=0, replay_map=None,
                  suite_order="variants-per-test"):
        """
        Run one or more tests and report with test result.

        :param params_list: a list of param dicts.
        :param variants: A varianter iterator (unused here)

        :return: a set with types of test failures.
        """
        del test_suite     # using self.job.references instead
        del variants            # we're not using multiplexation here
        if suite_order != "variants-per-test" and suite_order is not None:
            raise exceptions.JobError("execution-order %s is not supported "
                                      "for remote execution." % suite_order)
        del suite_order     # suite_order is ignored for now
        if not timeout:     # avoid timeout = 0
            timeout = None
        summary = set()

        stdout_backup = sys.stdout
        stderr_backup = sys.stderr
        fabric_debugfile = os.path.join(self.job.logdir, 'remote.log')
        paramiko_logger = logging.getLogger('paramiko')
        fabric_logger = logging.getLogger('avocado.fabric')
        remote_logger = logging.getLogger('avocado.remote')
        app_logger = logging.getLogger('avocado.debug')
        fmt = ('%(asctime)s %(module)-10.10s L%(lineno)-.4d %('
               'levelname)-5.5s| %(message)s')
        formatter = logging.Formatter(fmt=fmt, datefmt='%H:%M:%S')
        file_handler = logging.FileHandler(filename=fabric_debugfile)
        file_handler.setFormatter(formatter)
        fabric_logger.addHandler(file_handler)
        paramiko_logger.addHandler(file_handler)
        remote_logger.addHandler(file_handler)
        logger_list = [fabric_logger]
        if self.job.args.show_job_log:
            logger_list.append(app_logger)
            output.add_log_handler(paramiko_logger.name)
        sys.stdout = output.LoggingFile(logger=logger_list)
        sys.stderr = output.LoggingFile(logger=logger_list)
        try:
            try:
                self.setup()
                avocado_installed, _ = self.check_remote_avocado()
                if not avocado_installed:
                    raise exceptions.JobError('Remote machine does not seem to'
                                              ' have avocado installed')
            except Exception as details:
                stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
                raise exceptions.JobError(details)
            results = self.run_test(self.job.references, timeout)
            remote_log_dir = os.path.dirname(results['debuglog'])
            self.result.tests_total = results['total']
            local_log_dir = self.job.logdir
            for tst in results['tests']:
                name = tst['test'].split('-', 1)
                name = [name[0]] + name[1].split(';')
                if len(name) == 3:
                    name[2] = {"variant_id": name[2]}
                name = TestName(*name, no_digits=-1)
                state = dict(name=name,
                             time_elapsed=tst['time'],
                             time_start=tst['start'],
                             time_end=tst['end'],
                             status=tst['status'],
                             logdir=tst['logdir'],
                             logfile=tst['logfile'],
                             fail_reason=tst['fail_reason'],
                             job_logdir=local_log_dir,
                             job_unique_id='')
                self.result.start_test(state)
                self.job._result_events_dispatcher.map_method('start_test',
                                                              self.result,
                                                              state)
                self.result.check_test(state)
                self.job._result_events_dispatcher.map_method('end_test',
                                                              self.result,
                                                              state)
                if state['status'] == "INTERRUPTED":
                    summary.add("INTERRUPTED")
                elif not status.mapping[state['status']]:
                    summary.add("FAIL")
            zip_filename = remote_log_dir + '.zip'
            zip_path_filename = os.path.join(local_log_dir,
                                             os.path.basename(zip_filename))
            self.remote.receive_files(local_log_dir, zip_filename)
            archive.uncompress(zip_path_filename, local_log_dir)
            os.remove(zip_path_filename)
            self.result.end_tests()
            self.job._result_events_dispatcher.map_method('post_tests',
                                                          self.job)
        finally:
            try:
                self.tear_down()
            except Exception as details:
                stacktrace.log_exc_info(sys.exc_info(), logger=LOG_JOB)
                raise exceptions.JobError(details)
            sys.stdout = stdout_backup
            sys.stderr = stderr_backup
        return summary

    def tear_down(self):
        """
        This method is only called when `run_suite` gets to the point of to be
        executing `setup` method and is called at the end of the execution.

        :warning: It might be called on `setup` exceptions, so things
                  initialized during `setup` might not yet be initialized.
        """
        pass


class RemoteCLI(CLI):

    """
    Run tests on a remote machine
    """

    name = 'remote'
    description = "Remote machine options for 'run' subcommand"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        msg = 'test execution on a remote machine'
        remote_parser = run_subcommand_parser.add_argument_group(msg)
        remote_parser.add_argument('--remote-hostname',
                                   dest='remote_hostname', default=None,
                                   help=('Specify the hostname to login on'
                                         ' remote machine'))
        remote_parser.add_argument('--remote-port', dest='remote_port',
                                   default=22, type=int,
                                   help=('Specify the port number to login on '
                                         'remote machine. Default: %(default)s'))
        remote_parser.add_argument('--remote-username',
                                   dest='remote_username',
                                   default=getpass.getuser(),
                                   help=('Specify the username to login on'
                                         ' remote machine. Default: '
                                         '%(default)s'))
        remote_parser.add_argument('--remote-password',
                                   dest='remote_password', default=None,
                                   help=('Specify the password to login on'
                                         ' remote machine'))
        remote_parser.add_argument('--remote-key-file',
                                   dest='remote_key_file', default=None,
                                   help=('Specify an identity file with a '
                                         'private key instead of a password '
                                         '(Example: .pem files from Amazon EC2)'))
        remote_parser.add_argument('--remote-timeout', metavar='SECONDS',
                                   default=60, type=int,
                                   help=("Amount of time (in seconds) to "
                                         "wait for a successful connection"
                                         " to the remote machine. Defaults"
                                         " to %(default)s seconds."))

    @staticmethod
    def _check_required_args(args, enable_arg, required_args):
        """
        :return: True when enable_arg enabled and all required args are set
        :raise sys.exit: When missing required argument.
        """
        if (not hasattr(args, enable_arg) or
                not getattr(args, enable_arg)):
            return False
        missing = []
        for arg in required_args:
            if not getattr(args, arg):
                missing.append(arg)
        if missing:
            LOG_UI.error("Use of %s requires %s arguments to be set. Please "
                         "set %s.", enable_arg, ', '.join(required_args),
                         ', '.join(missing))

            return sys.exit(exit_codes.AVOCADO_FAIL)
        return True

    def run(self, args):
        if self._check_required_args(args, 'remote_hostname',
                                     ('remote_hostname',)):
            loader.loader.clear_plugins()
            loader.loader.register_plugin(loader.DummyLoader)
            args.test_runner = RemoteTestRunner
