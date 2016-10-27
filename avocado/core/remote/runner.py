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
# Copyright: Red Hat Inc. 2014-2015
# Author: Ruda Moura <rmoura@redhat.com>
"""Remote test runner."""

import sys
import json
import os
import re
import logging

from fabric.exceptions import CommandTimeout

from .test import RemoteTest
from .. import output
from .. import remoter
from .. import virt
from .. import exceptions
from .. import status
from ..runner import TestRunner
from ..test import TestName
from ...utils import astring
from ...utils import archive
from ...utils import stacktrace


class RemoteTestRunner(TestRunner):

    """ Tooled TestRunner to run on remote machine using ssh """

    # Let's use re.MULTILINE because sometimes servers might have MOTD
    # that will introduce a line break on output.
    remote_version_re = re.compile(r'^Avocado (\d+)\.(\d+)\r?$',
                                   re.MULTILINE)

    def __init__(self, job, result_proxy):
        super(RemoteTestRunner, self).__init__(job, result_proxy)
        #: remoter connection to the remote machine
        self.remote = None

    def setup(self):
        """ Setup remote environment and copy test directories """
        self.job.log.info("LOGIN      : %s@%s:%d (TIMEOUT: %s seconds)",
                          self.job.args.remote_username,
                          self.job.args.remote_hostname,
                          self.job.args.remote_port,
                          self.job.args.remote_timeout)
        self.remote = remoter.Remote(
            hostname=self.job.args.remote_hostname,
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

        match = self.remote_version_re.findall(result.stdout)
        if match is None:
            return (False, None)

        try:
            return (True, tuple(int(_) for _ in match[0]))
        except IndexError:
            return (False, None)

    @staticmethod
    def _parse_json_response(output):
        """
        Try to parse JSON response from the remote output.

        It tries to find start of the json dictionary and then grabs
        everything till the end of the dictionary. It supports single-
        line as well as multi-line pretty json output.
        """
        _result = iter(output.splitlines())
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

    def run_suite(self, test_suite, mux, timeout=0, replay_map=None):
        """
        Run one or more tests and report with test result.

        :param params_list: a list of param dicts.
        :param mux: A multiplex iterator (unused here)

        :return: a set with types of test failures.
        """
        del test_suite     # using self.job.references instead
        del mux            # we're not using multiplexation here
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
                stacktrace.log_exc_info(sys.exc_info(), logger='avocado.test')
                raise exceptions.JobError(details)
            results = self.run_test(self.job.references, timeout)
            remote_log_dir = os.path.dirname(results['debuglog'])
            self.result_proxy.set_tests_total(results['total'])
            self.result_proxy.start_tests()
            for tst in results['tests']:
                name = tst['test'].split('-', 1)
                name = [name[0]] + name[1].split(';')
                name = TestName(*name, no_digits=-1)
                test = RemoteTest(name=name,
                                  time=tst['time'],
                                  start=tst['start'],
                                  end=tst['end'],
                                  status=tst['status'],
                                  logdir=tst['logdir'],
                                  logfile=tst['logfile'],
                                  fail_reason=tst['fail_reason'])
                state = test.get_state()
                self.result_proxy.start_test(state)
                self.result_proxy.check_test(state)
                if state['status'] == "INTERRUPTED":
                    summary.add("INTERRUPTED")
                elif not status.mapping[state['status']]:
                    summary.add("FAIL")
            local_log_dir = self.job.logdir
            zip_filename = remote_log_dir + '.zip'
            zip_path_filename = os.path.join(local_log_dir,
                                             os.path.basename(zip_filename))
            self.remote.receive_files(local_log_dir, zip_filename)
            archive.uncompress(zip_path_filename, local_log_dir)
            os.remove(zip_path_filename)
            self.result_proxy.end_tests()
        finally:
            try:
                self.tear_down()
            except Exception as details:
                stacktrace.log_exc_info(sys.exc_info(), logger='avocado.test')
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


class VMTestRunner(RemoteTestRunner):

    """
    Test runner to run tests using libvirt domain
    """

    def __init__(self, job, result_proxy):
        super(VMTestRunner, self).__init__(job, result_proxy)
        #: VM used during testing
        self.vm = None

    def setup(self):
        """
        Initialize VM and establish connection
        """
        # Super called after VM is found and initialized
        self.job.log.info("DOMAIN     : %s", self.job.args.vm_domain)
        try:
            self.vm = virt.vm_connect(self.job.args.vm_domain,
                                      self.job.args.vm_hypervisor_uri)
        except virt.VirtError as exception:
            raise exceptions.JobError(exception.message)
        if self.vm.start() is False:
            e_msg = "Could not start VM '%s'" % self.job.args.vm_domain
            raise exceptions.JobError(e_msg)
        assert self.vm.domain.isActive() is not False
        # If hostname wasn't given, let's try to find out the IP address
        if self.job.args.vm_hostname is None:
            self.job.args.vm_hostname = self.vm.ip_address()
            if self.job.args.vm_hostname is None:
                e_msg = ("Could not find the IP address for VM '%s'. Please "
                         "set it explicitly with --vm-hostname" %
                         self.job.args.vm_domain)
                raise exceptions.JobError(e_msg)
        if self.job.args.vm_cleanup is True:
            self.vm.create_snapshot()
            if self.vm.snapshot is None:
                e_msg = ("Could not create snapshot on VM '%s'" %
                         self.job.args.vm_domain)
                raise exceptions.JobError(e_msg)
        # Finish remote setup and copy the tests
        self.job.args.remote_hostname = self.job.args.vm_hostname
        self.job.args.remote_port = self.job.args.vm_port
        self.job.args.remote_username = self.job.args.vm_username
        self.job.args.remote_password = self.job.args.vm_password
        self.job.args.remote_key_file = self.job.args.vm_key_file
        self.job.args.remote_timeout = self.job.args.vm_timeout
        super(VMTestRunner, self).setup()

    def tear_down(self):
        """
        Stop VM and restore snapshot (if asked for it)
        """
        super(VMTestRunner, self).tear_down()
        if (self.job.args.vm_cleanup is True and
                isinstance(getattr(self, 'vm', None), virt.VM)):
            self.vm.stop()
            if self.vm.snapshot is not None:
                self.vm.restore_snapshot()
            self.vm = None
