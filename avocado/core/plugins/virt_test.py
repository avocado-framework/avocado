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
# Copyright: Red Hat Inc. 2015
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Avocado virt-test compatibility wrapper
"""

import os
import sys
import logging
import Queue
import imp
import time

from avocado.core import result
from avocado.core import loader
from avocado.core.plugins import plugin
from avocado import test
from avocado.settings import settings
from avocado.settings import config_path_local
from avocado.utils import path

if 'VIRT_TEST_DIR' in os.environ:
    virt_test_dir = os.environ['VIRT_TEST_DIR']
else:
    virt_test_dir = settings.get_value(section='virt-test', key='test_suite_path', default=None)
    if virt_test_dir is None or not os.path.isdir(virt_test_dir):
        print('Virt test dir not set/invalid. Please make sure you add to %s' % config_path_local)
        print('')
        print('[virt-test]')
        print('test_suite_path=/valid/path/to/virt_test')
        print('')
        print('You can also export $VIRT_TEST_DIR (takes precedence over the config file)')
        print('$ export VIRT_TEST_DIR="/valid/path/to/virt_test"')
        sys.exit(1)

sys.path.append(os.path.expanduser(virt_test_dir))

from autotest.client import utils
from autotest.client.shared import error

from virttest import asset
from virttest import arch
from virttest import bootstrap
from virttest import cartesian_config
from virttest import data_dir
from virttest import defaults
from virttest import env_process
from virttest import funcatexit
from virttest import standalone_test
from virttest import utils_env
from virttest import utils_misc
from virttest import utils_params
from virttest import version

from virttest.standalone_test import SUPPORTED_LOG_LEVELS
from virttest.standalone_test import SUPPORTED_TEST_TYPES
from virttest.standalone_test import SUPPORTED_LIBVIRT_URIS
from virttest.standalone_test import SUPPORTED_LIBVIRT_DRIVERS
from virttest.standalone_test import SUPPORTED_IMAGE_TYPES
from virttest.standalone_test import SUPPORTED_DISK_BUSES
from virttest.standalone_test import SUPPORTED_NIC_MODELS
from virttest.standalone_test import SUPPORTED_NET_TYPES
from virttest.standalone_test import QEMU_DEFAULT_SET
from virttest.standalone_test import LIBVIRT_DEFAULT_SET
from virttest.standalone_test import LVSB_DEFAULT_SET
from virttest.standalone_test import OVS_DEFAULT_SET
from virttest.standalone_test import LIBVIRT_INSTALL
from virttest.standalone_test import LIBVIRT_REMOVE


class VirtTestResult(result.HumanTestResult):

    """
    Virt Test compatibility layer Result class.
    """

    def __init__(self, stream, args):
        """
        Creates an instance of RemoteTestResult.

        :param stream: an instance of :class:`avocado.core.output.View`.
        :param args: an instance of :class:`argparse.Namespace`.
        """
        result.HumanTestResult.__init__(self, stream, args)
        self.output = '-'
        self.setup()

    def setup(self):
        """
        Run the bootstrap needed before virt-test starts

        This usually includes downloading/restoring JeOS images, among others.
        """
        options = self.args
        test_dir = None
        if options.type:
            test_dir = data_dir.get_backend_dir(options.type)
        elif options.config:
            parent_config_dir = os.path.dirname(
                os.path.dirname(options.config))
            parent_config_dir = os.path.dirname(parent_config_dir)
            options.type = parent_config_dir
            test_dir = os.path.abspath(parent_config_dir)

        if options.type == 'qemu':
            check_modules = arch.get_kvm_module_list()
        else:
            check_modules = None
        online_docs_url = "https://github.com/autotest/virt-test/wiki"

        kwargs = {'test_name': options.type,
                  'test_dir': test_dir,
                  'base_dir': data_dir.get_data_dir(),
                  'default_userspace_paths': None,
                  'check_modules': check_modules,
                  'online_docs_url': online_docs_url,
                  'selinux': options.selinux_setup,
                  'restore_image': not(options.no_downloads or
                                       options.keep_image),
                  'interactive': False,
                  'update_providers': options.update_providers,
                  'guest_os': options.guest_os or defaults.DEFAULT_GUEST_OS}

        failed = False
        wait_message_printed = False

        bg = utils.InterruptedThread(bootstrap.bootstrap, kwargs=kwargs)
        t_begin = time.time()
        bg.start()

        while bg.isAlive():
            if not wait_message_printed:
                self.stream.notify(event='message', msg="SETUP      :  ", skip_newline=True)
                wait_message_printed = True
            self.stream.notify_progress(True)
            time.sleep(0.1)

        reason = None
        try:
            bg.join()
        except Exception, e:
            failed = True
            reason = e

        t_end = time.time()
        t_elapsed = t_end - t_begin
        state = dict()
        state['time_elapsed'] = t_elapsed
        if not failed:
            self.stream.set_test_status(status='PASS', state=state)
        else:
            self.stream.set_test_status(status='FAIL', state=state)
            self.stream.notify(event='error', msg="Setup error: %s" % reason)
            sys.exit(-1)

        return True


class VirtTestLoader(loader.TestLoader):

    def __init__(self, job):
        loader.TestLoader.__init__(self, job=job)

    def _get_parser(self):
        options_processor = VirtTestOptionsProcess(self.job)
        return options_processor.get_parser()

    def discover(self, params_list):
        """
        Discover tests for test suite.

        :param params_list: a list of test parameters.
        :type params_list: list
        :return: a test suite (a list of test factories).
        """
        test_suite = []
        for params in params_list:
            test_parameters = {'name': params['shortname'],
                               'base_logdir': self.job.logdir,
                               'params': params,
                               'job': self.job}
            test_suite.append((VirtTest, test_parameters))
        return test_suite

    def validate_ui(self, test_suite, ignore_missing=False,
                    ignore_not_test=False, ignore_broken_symlinks=False,
                    ignore_access_denied=False):
        pass

    def discover_url(self, url):
        cartesian_parser = self._get_parser()
        cartesian_parser.only_filter(url)
        params_list = [t for t in cartesian_parser.get_dicts()]
        return params_list


class VirtTest(test.Test):

    """
    Mininal test class used to run a virt test.
    """

    env_version = utils_env.get_env_version()

    def __init__(self, methodName='runTest', name=None, params=None,
                 base_logdir=None, tag=None, job=None, runner_queue=None):
        del name
        options = job.args

        self.bindir = data_dir.get_root_dir()
        self.virtdir = os.path.join(self.bindir, 'shared')
        self.builddir = os.path.join(self.bindir, 'backends', params.get("vm_type"))
        self.srcdir = path.init_dir(os.path.join(self.builddir, 'src'))
        self.tmpdir = path.init_dir(os.path.join(self.bindir, 'tmp'))

        self.iteration = 0
        if options.config:
            name = params.get("shortname")
        else:
            name = params.get("_short_name_map_file")["subtests.cfg"]
        self.outputdir = None
        self.resultsdir = None
        self.logfile = None
        self.file_handler = None
        self.background_errors = Queue.Queue()
        super(VirtTest, self).__init__(methodName=methodName, name=name, params=params, base_logdir=base_logdir,
                                       tag=tag, job=job, runner_queue=runner_queue)
        self.params = utils_params.Params(params)
        self.debugdir = self.logdir
        utils_misc.set_log_file_dir(self.logdir)

    def start_logging(self):
        super(VirtTest, self).start_logging()
        root_logger = logging.getLogger()
        root_logger.addHandler(self.file_handler)

    def stop_logging(self):
        super(VirtTest, self).stop_logging()
        root_logger = logging.getLogger()
        root_logger.removeHandler(self.file_handler)

    def write_test_keyval(self, d):
        self.whiteboard = str(d)

    def verify_background_errors(self):
        """
        Verify if there are any errors that happened on background threads.

        :raise Exception: Any exception stored on the background_errors queue.
        """
        try:
            exc = self.background_errors.get(block=False)
        except Queue.Empty:
            pass
        else:
            raise exc[1], None, exc[2]

    def runTest(self):
        params = self.params

        # If a dependency test prior to this test has failed, let's fail
        # it right away as TestNA.
        if params.get("dependency_failed") == 'yes':
            raise error.TestNAError("Test dependency failed")

        # Report virt test version
        logging.info(version.get_pretty_version_info())
        # Report the parameters we've received and write them as keyvals
        logging.info("Starting test %s", self.tag)
        logging.debug("Test parameters:")
        keys = params.keys()
        keys.sort()
        for key in keys:
            logging.debug("    %s = %s", key, params[key])

        # Warn of this special condition in related location in output & logs
        if os.getuid() == 0 and params.get('nettype', 'user') == 'user':
            logging.warning("")
            logging.warning("Testing with nettype='user' while running "
                            "as root may produce unexpected results!!!")
            logging.warning("")

        # Open the environment file
        env_filename = os.path.join(
            data_dir.get_backend_dir(params.get("vm_type")),
            params.get("env", "env"))
        env = utils_env.Env(env_filename, self.env_version)

        test_passed = False
        t_type = None

        try:
            try:
                try:
                    subtest_dirs = []

                    other_subtests_dirs = params.get("other_tests_dirs", "")
                    for d in other_subtests_dirs.split():
                        d = os.path.join(*d.split("/"))
                        subtestdir = os.path.join(self.bindir, d, "tests")
                        if not os.path.isdir(subtestdir):
                            raise error.TestError("Directory %s does not "
                                                  "exist" % subtestdir)
                        subtest_dirs += data_dir.SubdirList(subtestdir,
                                                            bootstrap.test_filter)

                    provider = params.get("provider", None)

                    if provider is None:
                        # Verify if we have the correspondent source file for
                        # it
                        for generic_subdir in asset.get_test_provider_subdirs('generic'):
                            subtest_dirs += data_dir.SubdirList(generic_subdir,
                                                                bootstrap.test_filter)

                        for specific_subdir in asset.get_test_provider_subdirs(params.get("vm_type")):
                            subtest_dirs += data_dir.SubdirList(
                                specific_subdir, bootstrap.test_filter)
                    else:
                        provider_info = asset.get_test_provider_info(provider)
                        for key in provider_info['backends']:
                            subtest_dirs += data_dir.SubdirList(
                                provider_info['backends'][key]['path'],
                                bootstrap.test_filter)

                    subtest_dir = None

                    # Get the test routine corresponding to the specified
                    # test type
                    logging.debug("Searching for test modules that match "
                                  "'type = %s' and 'provider = %s' "
                                  "on this cartesian dict",
                                  params.get("type"), params.get("provider", None))

                    t_types = params.get("type").split()
                    # Make sure we can load provider_lib in tests
                    for s in subtest_dirs:
                        if os.path.dirname(s) not in sys.path:
                            sys.path.insert(0, os.path.dirname(s))

                    test_modules = {}
                    for t_type in t_types:
                        for d in subtest_dirs:
                            module_path = os.path.join(d, "%s.py" % t_type)
                            if os.path.isfile(module_path):
                                logging.debug("Found subtest module %s",
                                              module_path)
                                subtest_dir = d
                                break
                        if subtest_dir is None:
                            msg = ("Could not find test file %s.py on test"
                                   "dirs %s" % (t_type, subtest_dirs))
                            raise error.TestError(msg)
                        # Load the test module
                        f, p, d = imp.find_module(t_type, [subtest_dir])
                        test_modules[t_type] = imp.load_module(t_type, f, p, d)
                        f.close()

                    # Preprocess
                    try:
                        params = env_process.preprocess(self, params, env)
                    finally:
                        env.save()

                    # Run the test function
                    for t_type in t_types:
                        test_module = test_modules[t_type]
                        run_func = utils_misc.get_test_entrypoint_func(
                            t_type, test_module)
                        try:
                            run_func(self, params, env)
                            self.verify_background_errors()
                        finally:
                            env.save()
                    test_passed = True
                    error_message = funcatexit.run_exitfuncs(env, t_type)
                    if error_message:
                        raise error.TestWarn("funcatexit failed with: %s"
                                             % error_message)

                except Exception:
                    if t_type is not None:
                        error_message = funcatexit.run_exitfuncs(env, t_type)
                        if error_message:
                            logging.error(error_message)
                    try:
                        env_process.postprocess_on_error(self, params, env)
                    finally:
                        env.save()
                    raise

            finally:
                # Postprocess
                try:
                    try:
                        env_process.postprocess(self, params, env)
                    except Exception, e:
                        if test_passed:
                            raise
                        logging.error("Exception raised during "
                                      "postprocessing: %s", e)
                finally:
                    env.save()

        except Exception, e:
            if params.get("abort_on_error") != "yes":
                raise
            # Abort on error
            logging.info("Aborting job (%s)", e)
            if params.get("vm_type") == "qemu":
                for vm in env.get_all_vms():
                    if vm.is_dead():
                        continue
                    logging.info("VM '%s' is alive.", vm.name)
                    for m in vm.monitors:
                        logging.info("It has a %s monitor unix socket at: %s",
                                     m.protocol, m.filename)
                    logging.info("The command line used to start it was:\n%s",
                                 vm.make_qemu_command())
                raise error.JobError("Abort requested (%s)" % e)

        return test_passed


class VirtTestOptionsProcess(object):

    """
    Pick virt test options and parse them to get to a cartesian parser.
    """

    def __init__(self, job):
        """
        Parses options and initializes attributes.
        """
        self.options = job.args
        self.view = job.view
        self.cartesian_parser = None

    def _process_qemu_bin(self):
        """
        Puts the value of the qemu bin option in the cartesian parser command.
        """
        if self.options.config and self.options.qemu is None:
            logging.info("Config provided and no --vt-qemu-bin set. Not trying "
                         "to automatically set qemu bin.")
        else:
            (qemu_bin_path, qemu_img_path, qemu_io_path,
             qemu_dst_bin_path) = standalone_test.find_default_qemu_paths(self.options.qemu,
                                                                          self.options.dst_qemu)
            self.cartesian_parser.assign("qemu_binary", qemu_bin_path)
            self.cartesian_parser.assign("qemu_img_binary", qemu_img_path)
            self.cartesian_parser.assign("qemu_io_binary", qemu_io_path)
            if qemu_dst_bin_path is not None:
                self.cartesian_parser.assign("qemu_dst_binary",
                                             qemu_dst_bin_path)

    def _process_qemu_img(self):
        """
        Puts the value of the qemu bin option in the cartesian parser command.
        """
        if self.options.config and self.options.qemu is None:
            logging.info("Config provided and no --vt-qemu-bin set. Not trying "
                         "to automatically set qemu bin.")
        else:
            (_, qemu_img_path,
             _, _) = standalone_test.find_default_qemu_paths(self.options.qemu,
                                                             self.options.dst_qemu)
            self.cartesian_parser.assign("qemu_img_binary", qemu_img_path)

    def _process_qemu_accel(self):
        """
        Puts the value of the qemu bin option in the cartesian parser command.
        """
        if self.options.accel == 'tcg':
            self.cartesian_parser.assign("disable_kvm", "yes")

    def _process_bridge_mode(self):
        if self.options.nettype not in SUPPORTED_NET_TYPES:
            self.view.notify(event='error', msg="Invalid --vt-nettype option '%s'. Valid options are: (%s)" %
                             (self.options.nettype, ", ".join(SUPPORTED_NET_TYPES)))
            sys.exit(1)
        if self.options.nettype == 'bridge':
            if os.getuid() != 0:
                self.view.notify(event='error', msg="In order to use bridge, you need to be root, aborting...")
                sys.exit(1)
            self.cartesian_parser.assign("nettype", "bridge")
            self.cartesian_parser.assign("netdst", self.options.netdst)
        elif self.options.nettype == 'user':
            self.cartesian_parser.assign("nettype", "user")
        elif self.options.nettype == 'none':
            self.cartesian_parser.assign("nettype", "none")

    def _process_monitor(self):
        if self.options.monitor == 'qmp':
            self.cartesian_parser.assign("monitors", "qmp1")
            self.cartesian_parser.assign("monitor_type_qmp1", "qmp")

    def _process_smp(self):
        if not self.options.config:
            if self.options.smp == '1':
                self.cartesian_parser.only_filter("up")
            elif self.options.smp == '2':
                self.cartesian_parser.only_filter("smp2")
            else:
                try:
                    self.cartesian_parser.only_filter("up")
                    self.cartesian_parser.assign("smp", int(self.options.smp))
                except ValueError:
                    self.view.notify(event='error', msg="Invalid option for smp: %s, aborting..." % self.options.smp)
                    sys.exit(1)
        else:
            logging.info("Config provided, ignoring --vt-smp option")

    def _process_arch(self):
        if self.options.arch is None:
            pass
        elif not self.options.config:
            self.cartesian_parser.only_filter(self.options.arch)
        else:
            logging.info("Config provided, ignoring --vt-arch option")

    def _process_machine_type(self):
        if not self.options.config:
            if self.options.machine_type is None:
                # TODO: this is x86-specific, instead we can get the default
                # arch from qemu binary and run on all supported machine types
                if self.options.arch is None and self.options.guest_os is None:
                    import virttest.defaults
                    self.cartesian_parser.only_filter(
                        virttest.defaults.DEFAULT_MACHINE_TYPE)
            else:
                self.cartesian_parser.only_filter(self.options.machine_type)
        else:
            logging.info("Config provided, ignoring --vt-machine-type option")

    def _process_image_type(self):
        if not self.options.config:
            if self.options.image_type in SUPPORTED_IMAGE_TYPES:
                self.cartesian_parser.only_filter(self.options.image_type)
            else:
                self.cartesian_parser.only_filter("raw")
                # The actual param name is image_format.
                self.cartesian_parser.assign("image_format",
                                             self.options.image_type)
        else:
            logging.info("Config provided, ignoring --vt-image-type option")

    def _process_nic_model(self):
        if not self.options.config:
            if self.options.nic_model in SUPPORTED_NIC_MODELS:
                self.cartesian_parser.only_filter(self.options.nic_model)
            else:
                self.cartesian_parser.only_filter("nic_custom")
                self.cartesian_parser.assign(
                    "nic_model", self.options.nic_model)
        else:
            logging.info("Config provided, ignoring --vt-nic-model option")

    def _process_disk_buses(self):
        if not self.options.config:
            if self.options.disk_bus in SUPPORTED_DISK_BUSES:
                self.cartesian_parser.only_filter(self.options.disk_bus)
            else:
                self.view.notify(event='error', msg=("Option %s is not in the list %s, aborting..." %
                                                     (self.options.disk_bus, SUPPORTED_DISK_BUSES)))
                sys.exit(1)
        else:
            logging.info("Config provided, ignoring --vt-disk-bus option")

    def _process_vhost(self):
        if not self.options.config:
            if self.options.nettype == "bridge":
                if self.options.vhost == "on":
                    self.cartesian_parser.assign("vhost", "on")
                elif self.options.vhost == "force":
                    self.cartesian_parser.assign("netdev_extra_params",
                                                 '",vhostforce=on"')
                    self.cartesian_parser.assign("vhost", "on")
            else:
                if self.options.vhost in ["on", "force"]:
                    self.view.notify(event='error', msg=("Nettype %s is incompatible with vhost %s, aborting..." %
                                                         (self.options.nettype, self.options.vhost)))
                    sys.exit(1)
        else:
            logging.info("Config provided, ignoring --vt-vhost option")

    def _process_qemu_sandbox(self):
        if not self.options.config:
            if self.options.qemu_sandbox == "off":
                self.cartesian_parser.assign("qemu_sandbox", "off")
        else:
            logging.info("Config provided, ignoring \"--vt-sandbox <on|off>\" option")

    def _process_malloc_perturb(self):
        self.cartesian_parser.assign("malloc_perturb",
                                     self.options.malloc_perturb)

    def _process_qemu_specific_options(self):
        """
        Calls for processing all options specific to the qemu test.

        This method modifies the cartesian set by parsing additional lines.
        """

        self._process_qemu_bin()
        self._process_qemu_accel()
        self._process_monitor()
        self._process_smp()
        self._process_image_type()
        self._process_nic_model()
        self._process_disk_buses()
        self._process_vhost()
        self._process_malloc_perturb()
        self._process_qemu_sandbox()

    def _process_lvsb_specific_options(self):
        """
        Calls for processing all options specific to lvsb test
        """
        self.options.no_downloads = True

    def _process_libvirt_specific_options(self):
        """
        Calls for processing all options specific to libvirt test.
        """
        if self.options.uri:
            driver_found = False
            for driver in SUPPORTED_LIBVIRT_DRIVERS:
                if self.options.uri.count(driver):
                    driver_found = True
                    self.cartesian_parser.only_filter(driver)
            if not driver_found:
                self.view.notify(event='error', msg="Unsupported uri: %s." % self.options.uri)
                sys.exit(1)
        else:
            self.cartesian_parser.only_filter("qemu")

    def _process_guest_os(self):
        if not self.options.config:
            if len(standalone_test.get_guest_name_list(self.options)) == 0:
                self.view.notify(event='error', msg="Guest name %s is not on the known guest os list "
                                                    "(see --vt-list-guests), aborting..." % self.options.guest_os)
                sys.exit(1)
            self.cartesian_parser.only_filter(
                self.options.guest_os or defaults.DEFAULT_GUEST_OS)
        else:
            logging.info("Config provided, ignoring --vt-guest-os option")

    def _process_list(self):
        if self.options.list:
            standalone_test.print_test_list(self.options,
                                            self.cartesian_parser)
            sys.exit(0)
        if self.options.list_guests:
            standalone_test.print_guest_list(self.options)
            sys.exit(0)

    def _process_tests(self):
        if not self.options.config:
            if self.options.type:
                if self.options.url and self.options.dropin:
                    self.view.notify(event='error', msg="Option --vt-tests and --vt-run-dropin can't be set at "
                                                        "the same time")
                    sys.exit(1)
                elif self.options.url:
                    tests = self.options.url
                    if self.options.type == 'libvirt':
                        if self.options.install_guest:
                            tests.insert(0, LIBVIRT_INSTALL)
                        if self.options.remove_guest:
                            tests.append(LIBVIRT_REMOVE)
                    self.cartesian_parser.only_filter(", ".join(tests))
                elif self.options.dropin:
                    dropin_tests = os.listdir(os.path.join(data_dir.get_root_dir(), "dropin"))
                    if len(dropin_tests) <= 1:
                        self.view.notify(event='error', msg="No drop in tests detected, aborting. "
                                                            "Make sure you have scripts on the 'dropin' "
                                                            "directory")
                        sys.exit(1)
                    self.cartesian_parser.only_filter("dropin")
                else:
                    if self.options.type == 'qemu':
                        self.cartesian_parser.only_filter(QEMU_DEFAULT_SET)
                        self.cartesian_parser.no_filter("with_reboot")
                    elif self.options.type == 'libvirt':
                        self.cartesian_parser.only_filter(LIBVIRT_DEFAULT_SET)
                    elif self.options.type == 'lvsb':
                        self.cartesian_parser.only_filter(LVSB_DEFAULT_SET)
                    elif self.options.type == 'openvswitch':
                        self.cartesian_parser.only_filter(OVS_DEFAULT_SET)
        else:
            logging.info("Config provided, ignoring --vt-tests option")

    def _process_restart_vm(self):
        if not self.options.config:
            if not self.options.keep_guest_running:
                self.cartesian_parser.assign("kill_vm", "yes")

    def _process_restore_image_between_tests(self):
        if not self.options.config:
            if not self.options.keep_image_between_tests:
                self.cartesian_parser.assign("restore_image", "yes")

    def _process_mem(self):
        self.cartesian_parser.assign("mem", self.options.mem)

    def _process_tcpdump(self):
        """
        Verify whether we can run tcpdump. If we can't, turn it off.
        """
        try:
            tcpdump_path = utils_misc.find_command('tcpdump')
        except ValueError:
            tcpdump_path = None

        non_root = os.getuid() != 0

        if tcpdump_path is None or non_root:
            self.cartesian_parser.assign("run_tcpdump", "no")

    def _process_no_filter(self):
        if not self.options.config:
            if self.options.no_filter:
                no_filter = ", ".join(self.options.no_filter.split(' '))
                self.cartesian_parser.no_filter(no_filter)

    def _process_only_type_specific(self):
        if not self.options.config:
            if self.options.only_type_specific:
                self.cartesian_parser.only_filter("(subtest=type_specific)")

    def _process_general_options(self):
        """
        Calls for processing all generic options.

        This method modifies the cartesian set by parsing additional lines.
        """
        self._process_guest_os()
        self._process_arch()
        self._process_machine_type()
        self._process_restart_vm()
        self._process_restore_image_between_tests()
        self._process_mem()
        self._process_tcpdump()
        self._process_no_filter()
        self._process_qemu_img()
        self._process_bridge_mode()
        self._process_only_type_specific()

    def _process_options(self):
        """
        Process the options given in the command line.
        """

        if (not self.options.type) and (not self.options.config):
            self.view.notify(event='error',
                             msg="No type (--vt-type) or config (--vt-config) options specified, aborting...")
            sys.exit(0)

        if self.options.type:
            if self.options.type not in SUPPORTED_TEST_TYPES:
                self.view.notify(event='error', msg="Invalid test type %s. Valid test types: %s. Aborting..." %
                                                    (self.options.type, " ".join(SUPPORTED_TEST_TYPES)))
                sys.exit(1)

        if self.options.vt_log_level not in SUPPORTED_LOG_LEVELS:
            self.view.notify(event='error', msg="Invalid log level '%s'. Valid log levels: %s. "
                                                "Aborting..." % (self.options.vt_log_level,
                                                                 " ".join(SUPPORTED_LOG_LEVELS)))
            sys.exit(1)
        num_level = getattr(logging, self.options.vt_log_level.upper(), None)
        self.options.log_level = num_level

        if self.options.vt_console_level not in SUPPORTED_LOG_LEVELS:
            self.view.notify(event='error', msg="Invalid console level '%s'. Valid console levels: %s. Aborting..." %
                                                (self.options.vt_console_level, " ".join(SUPPORTED_LOG_LEVELS)))
            sys.exit(1)
        num_level_console = getattr(logging,
                                    self.options.vt_console_level.upper(),
                                    None)
        self.options.console_level = num_level_console

        if self.options.datadir:
            data_dir.set_backing_data_dir(self.options.datadir)

        standalone_test.create_config_files(self.options)

        self.cartesian_parser = cartesian_config.Parser(debug=False)

        if self.options.config:
            cfg = os.path.abspath(self.options.config)

        if not self.options.config:
            cfg = data_dir.get_backend_cfg_path(self.options.type, 'tests.cfg')

        self.cartesian_parser.parse_file(cfg)
        if self.options.type != 'lvsb':
            self._process_general_options()

        if self.options.type == 'qemu':
            self._process_qemu_specific_options()
        elif self.options.type == 'lvsb':
            self._process_lvsb_specific_options()
        elif self.options.type == 'openvswitch':
            self._process_qemu_specific_options()
        elif self.options.type == 'libvirt':
            self._process_libvirt_specific_options()
        # List and tests have to be the last things to be processed
        self._process_list()
        # Tests won't be processed here. The code of the function will
        # be utilized elsewhere.
        # self._process_tests()

    def get_parser(self):
        standalone_test.handle_stdout(self.options)
        self._process_options()
        standalone_test.reset_logging()
        standalone_test.configure_console_logging(loglevel=self.options.console_level)
        return self.cartesian_parser


class VirtTestCompatPlugin(plugin.Plugin):

    """
    Implements the avocado virt test options
    """

    name = 'virt_test_compat_runner'
    enabled = True

    def configure(self, parser):
        """
        Add the subparser for the run action.

        :param parser: Main test runner parser.
        """
        self.parser = parser
        vt_compat_group = parser.runner.add_argument_group('Virt-Test compatibility layer options')

        try:
            qemu_bin_path = standalone_test.find_default_qemu_paths()[0]
        except ValueError:
            qemu_bin_path = "Could not find one"

        if os.getuid() == 0:
            nettype_default = 'bridge'
        else:
            nettype_default = 'user'

        vt_compat_group.add_argument("--vt-verbose", action="store_true",
                                     dest="verbose", help=("Exhibit test "
                                                           "messages in the console "
                                                           "(used for debugging)"))
        vt_compat_group.add_argument("--vt-console-level", action="store",
                                     dest="vt_console_level",
                                     default="debug",
                                     help=("Log level of test messages in the console. Only valid "
                                           "with --vt-verbose. "
                                           "Supported levels: " +
                                           ", ".join(SUPPORTED_LOG_LEVELS) +
                                           ". Default: "))
        vt_compat_group.add_argument("--vt-show-open-fd", action="store_true",
                                     dest="show_open_fd", help=("Show how many "
                                                                "open fds at the end of "
                                                                "each test "
                                                                "(used for debugging)"))

        vt_compat_group.add_argument("--vt-bootstrap", action="store_true",
                                     dest="bootstrap", help=("Perform test suite setup "
                                                             "procedures, such as "
                                                             "downloading JeOS and check "
                                                             "required programs and "
                                                             "libs. Requires --vt-type to be set"))
        vt_compat_group.add_argument("--vt-update-config", action="store_true",
                                     default=False,
                                     dest="update_config", help=("Forces configuration "
                                                                 "updates (all manual "
                                                                 "config file editing "
                                                                 "will be lost). "
                                                                 "Requires --vt-type to be set"))
        vt_compat_group.add_argument("--vt-update-providers", action="store_true",
                                     default=False,
                                     dest="update_providers", help=("Forces test "
                                                                    "providers to be "
                                                                    "updated (git repos "
                                                                    "will be pulled)"))
        vt_compat_group.add_argument("--vt-type", action="store", dest="type",
                                     help="Choose test type (%s)" % ", ".join(SUPPORTED_TEST_TYPES),
                                     default='qemu')
        vt_compat_group.add_argument("--vt-connect-uri", action="store", dest="uri",
                                     help="Choose test connect uri for libvirt (E.g: %s)" %
                                     ", ".join(SUPPORTED_LIBVIRT_URIS))
        vt_compat_group.add_argument("--vt-config", action="store", dest="config",
                                     help=("Explicitly choose a cartesian config. "
                                           "When choosing this, some options will be "
                                           "ignored"))
        vt_compat_group.add_argument("--vt-no-downloads", action="store_true",
                                     dest="no_downloads", default=False,
                                     help="Do not attempt to download JeOS images")
        vt_compat_group.add_argument("--vt-selinux-setup", action="store_true",
                                     dest="selinux_setup", default=False,
                                     help="Define default contexts of directory.")
        vt_compat_group.add_argument("--vt-setup", action="store_true",
                                     dest="vt_setup",
                                     help="Run virt test setup actions (download/restore jeos image)")
        vt_compat_group.add_argument("--vt-keep-image", action="store_true",
                                     dest="keep_image",
                                     help=("Don't restore the JeOS image from pristine "
                                           "at the beginning of the test suite run "
                                           "(faster but unsafe). Has no effect unless --vt-setup is provided"))
        vt_compat_group.add_argument("--vt-keep-image-between-tests",
                                     action="store_true", default=False,
                                     dest="keep_image_between_tests",
                                     help=("Don't restore the JeOS image from pristine "
                                           "between tests (faster but unsafe). Has no effect unless "
                                           "--vt-setup is provided"))
        vt_compat_group.add_argument("--vt-guest-os", action="store", dest="guest_os",
                                     default=None,
                                     help=("Select the guest OS to be used. "
                                           "If -c is provided, this will be ignored. "
                                           "Default: %s" % defaults.DEFAULT_GUEST_OS))
        vt_compat_group.add_argument("--vt-arch", action="store", dest="arch",
                                     default=None,
                                     help=("Architecture under test. "
                                           "If -c is provided, this will be ignored. "
                                           "Default: any that supports the given machine type"))
        vt_compat_group.add_argument("--vt-machine-type", action="store", dest="machine_type",
                                     default=None,
                                     help=("Machine type under test. "
                                           "If -c is provided, this will be ignored. "
                                           "Default: all for the chosen guests, %s if "
                                           "--vt-guest-os not given." % defaults.DEFAULT_MACHINE_TYPE))
        vt_compat_group.add_argument("--vt-list-tests", action="store_true", dest="list",
                                     help="List tests available")
        vt_compat_group.add_argument("--vt-list-guests", action="store_true",
                                     dest="list_guests",
                                     help="List guests available")
        vt_compat_group.add_argument("--vt-logs-dir", action="store", dest="logdir",
                                     help=("Path to the logs directory. "
                                           "Default path: %s" % os.path.join(data_dir.get_backing_data_dir(), 'logs')))
        vt_compat_group.add_argument("--vt-data-dir", action="store", dest="datadir",
                                     help=("Path to a data dir. "
                                           "Default path: %s" % data_dir.get_data_dir()))
        vt_compat_group.add_argument("--vt-keep-guest-running", action="store_true",
                                     dest="keep_guest_running", default=False,
                                     help=("Don't shut down guests at the end of each "
                                           "test (faster but unsafe)"))
        vt_compat_group.add_argument("--vt-mem", action="store", dest="mem",
                                     default="1024",
                                     help=("RAM dedicated to the main VM. Default:"
                                           ""))
        vt_compat_group.add_argument("--vt-no", action="store", dest="no_filter", default="",
                                     help=("List of space separated no filters to be "
                                           "passed to the config parser. If -c is "
                                           "provided, this will be ignored"))
        vt_compat_group.add_argument("--vt-type-specific", action="store_true",
                                     dest="only_type_specific", default=False,
                                     help=("Enable only type specific tests. Shared"
                                           " tests will not be tested."))

        vt_compat_group.add_argument("--vt-run-dropin", action="store_true", dest="dropin",
                                     default=False,
                                     help=("Run tests present on the drop in dir on the "
                                           "host. Incompatible with --vt-tests."))

        vt_compat_group.add_argument("--vt-log-level", action="store", dest="vt_log_level",
                                     default="debug",
                                     help=("Set log level for top level log file."
                                           " Supported levels: " +
                                           ", ".join(SUPPORTED_LOG_LEVELS) +
                                           ". Default: "))

        vt_compat_group.add_argument("--vt-no-cleanup", action="store_true",
                                     dest="no_cleanup",
                                     default=False,
                                     help=("Don't clean up tmp files or VM processes at "
                                           "the end of a virt-test execution (useful "
                                           "for debugging)"))

        vt_compat_group.add_argument("--vt-qemu-bin", action="store", dest="qemu",
                                     default=None,
                                     help=("Path to a custom qemu binary to be tested. "
                                           "If -c is provided and this flag is omitted, "
                                           "no attempt to set the qemu binaries will be made. "
                                           "Default path: %s" % qemu_bin_path))
        vt_compat_group.add_argument("--vt-qemu-dst-bin", action="store", dest="dst_qemu",
                                     default=None,
                                     help=("Path to a custom qemu binary to be tested for "
                                           "the destination of a migration, overrides "
                                           "--vt-qemu-bin. "
                                           "If -c is provided and this flag is omitted, "
                                           "no attempt to set the qemu binaries will be made. "
                                           "Default path: %s" % qemu_bin_path))
        vt_compat_group.add_argument("--vt-use-malloc-perturb", action="store",
                                     dest="malloc_perturb", default="yes",
                                     help=("Use MALLOC_PERTURB_ env variable set to 1 "
                                           "to help catch memory allocation problems on "
                                           "qemu (yes or no). Default: "))
        vt_compat_group.add_argument("--vt-accel", action="store", dest="accel", default="kvm",
                                     help=("Accelerator used to run qemu (kvm or tcg). "
                                           "Default: kvm"))
        help_msg = "QEMU network option (%s). " % ", ".join(SUPPORTED_NET_TYPES)
        help_msg += "Default: "
        vt_compat_group.add_argument("--vt-nettype", action="store", dest="nettype",
                                     default=nettype_default, help=help_msg)
        vt_compat_group.add_argument("--vt-netdst", action="store", dest="netdst",
                                     default="virbr0",
                                     help=("Bridge name to be used "
                                           "(if you chose bridge as nettype). "
                                           "Default: "))
        vt_compat_group.add_argument("--vt-vhost", action="store", dest="vhost",
                                     default="off",
                                     help=("Whether to enable vhost for qemu "
                                           "(on/off/force). Depends on nettype=bridge. "
                                           "If -c is provided, this will be ignored. "
                                           "Default: "))
        vt_compat_group.add_argument("--vt-monitor", action="store", dest="monitor",
                                     default='human',
                                     help="Monitor type (human or qmp). Default: ")
        vt_compat_group.add_argument("--vt-smp", action="store", dest="smp",
                                     default='2',
                                     help=("Number of virtual cpus to use. "
                                           "If -c is provided, this will be ignored. "
                                           "Default: "))
        vt_compat_group.add_argument("--vt-image-type", action="store", dest="image_type",
                                     default="qcow2",
                                     help=("Image format type to use "
                                           "(any valid qemu format). "
                                           "If -c is provided, this will be ignored. "
                                           "Default: "))
        vt_compat_group.add_argument("--vt-nic-model", action="store", dest="nic_model",
                                     default="virtio_net",
                                     help=("Guest network card model. "
                                           "If -c is provided, this will be ignored. "
                                           "(any valid qemu format). Default: "))
        vt_compat_group.add_argument("--vt-disk-bus", action="store", dest="disk_bus",
                                     default="virtio_blk",
                                     help=("Guest main image disk bus. One of " +
                                           " ".join(SUPPORTED_DISK_BUSES) +
                                           ". If -c is provided, this will be ignored. "
                                           "Default: "))
        vt_compat_group.add_argument("--vt-qemu_sandbox", action="store", dest="qemu_sandbox",
                                     default="on",
                                     help=("Enable qemu sandboxing "
                                           "(on/off). Default: "))

        vt_compat_group.add_argument("--vt-install", action="store_true",
                                     dest="install_guest",
                                     help=("Install the guest using import method before "
                                           "the tests are run."))
        vt_compat_group.add_argument("--vt-remove", action="store_true", dest="remove_guest",
                                     help=("Remove the guest from libvirt. This will not "
                                           "delete the guest's disk file."))

        self.configured = True

    def activate(self, args):
        """
        Run test modules or simple tests.

        :param args: Command line args received from the run subparser.
        """
        if getattr(args, 'vt_setup', False):
            self.parser.application.set_defaults(vt_loader=VirtTestLoader, vt_result=VirtTestResult)
        else:
            self.parser.application.set_defaults(vt_loader=VirtTestLoader)
