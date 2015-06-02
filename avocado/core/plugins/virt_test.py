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
import time

from avocado.core import result
from avocado.core import loader
from avocado.core import output
from avocado.core import exceptions
from avocado.core.plugins import plugin
from avocado import test
from avocado.settings import settings
from avocado.utils import path
from avocado import multiplexer

# virt-test supports using autotest from a git checkout, so we'll have to
# support that as well. The code below will pick up the environment variable
# $AUTOTEST_PATH and do the import magic needed to make the autotest library
# available in the system.
AUTOTEST_PATH = None

if 'AUTOTEST_PATH' in os.environ:
    AUTOTEST_PATH = os.path.expanduser(os.environ['AUTOTEST_PATH'])
    client_dir = os.path.join(os.path.abspath(AUTOTEST_PATH), 'client')
    setup_modules_path = os.path.join(client_dir, 'setup_modules.py')
    import imp
    setup_modules = imp.load_source('autotest_setup_modules',
                                    setup_modules_path)
    setup_modules.setup(base_path=client_dir,
                        root_module_name="autotest.client")

from autotest.client import utils
from autotest.client.shared import error

# The code below is used by this plugin to find the virt test directory,
# so that it can load the virttest python lib, used by the plugin code.
# If the user doesn't provide the proper configuration, the plugin will
# fail to load.
VIRT_TEST_PATH = None

if 'VIRT_TEST_PATH' in os.environ:
    VIRT_TEST_PATH = os.environ['VIRT_TEST_PATH']
else:
    VIRT_TEST_PATH = settings.get_value(section='virt_test',
                                        key='virt_test_path', default=None)

if VIRT_TEST_PATH is not None:
    sys.path.append(os.path.expanduser(VIRT_TEST_PATH))

from virttest import asset
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
from virttest import storage

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
        Run the setup needed before tests start to run (restore test images).
        """
        options = self.args
        if options.vt_config:
            parent_config_dir = os.path.dirname(os.path.dirname(options.vt_config))
            parent_config_dir = os.path.dirname(parent_config_dir)
            options.vt_type = parent_config_dir

        kwargs = {'options': options}

        failed = False

        bg = utils.InterruptedThread(bootstrap.setup, kwargs=kwargs)
        t_begin = time.time()
        bg.start()

        self.stream.notify(event='message', msg="SETUP      :  ", skip_newline=True)
        while bg.isAlive():
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


def configure_console_logging(loglevel=logging.DEBUG):
    """
    Simple helper for adding a file logger to the root logger.
    """
    logger = logging.getLogger()
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(loglevel)

    fmt = ('%(asctime)s %(module)-10.10s L%(lineno)-.4d %('
           'levelname)-5.5s| %(message)s')
    formatter = logging.Formatter(fmt=fmt, datefmt='%H:%M:%S')

    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return stream_handler


def configure_file_logging(logfile, loglevel=logging.DEBUG):
    """
    Add a file logger to the root logger.

    This file logger contains the formatting of the avocado
    job log. This way all things logged by autotest go
    straight to the avocado job log.
    """
    logger = logging.getLogger()
    file_handler = logging.FileHandler(filename=logfile)
    file_handler.setLevel(loglevel)
    fmt = ('%(asctime)s %(module)-10.10s L%(lineno)-.4d %('
           'levelname)-5.5s| %(message)s')
    formatter = logging.Formatter(fmt=fmt, datefmt='%H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return file_handler


def guest_listing(options, view):
    term_support = output.TermSupport()
    if options.vt_type == 'lvsb':
        view.notify(event='error',
                    msg="No guest types available for lvsb testing")
        sys.exit(1)
    index = 0
    view.notify(event='minor', msg=("Searched %s for guest images\n" %
                                    os.path.join(data_dir.get_data_dir(),
                                                 'images')))
    view.notify(event='minor', msg="Available guests in config:")
    view.notify(msg='')
    for params in standalone_test.get_guest_name_parser(options).get_dicts():
        index += 1
        base_dir = params.get("images_base_dir", data_dir.get_data_dir())
        image_name = storage.get_image_filename(params, base_dir)
        name = params['name']
        if os.path.isfile(image_name):
            out = name
        else:
            out = (name + " " +
                   term_support.warn_header_str("(missing %s)" %
                                                os.path.basename(image_name)))
        view.notify(event='minor', msg=out)


class VirtTestListJob(object):

    """
    Mock Job class, used to provide test loaders with a Job object with enough
    options data for test listing purposes.
    """

    def __init__(self, args):
        self.view = output.View()
        self.logfile = None
        self.logdir = '.'
        self.args = args
        self.args.vt_config = None
        self.args.vt_verbose = True
        self.args.vt_log_level = 'debug'
        self.args.vt_console_level = 'debug'
        self.args.vt_datadir = data_dir.get_data_dir()
        self.args.vt_config = None
        self.args.vt_arch = None
        self.args.vt_machine_type = None
        self.args.vt_keep_guest_running = False
        self.args.vt_keep_image_between_tests = False
        self.args.vt_mem = 1024
        self.args.vt_no_filter = ''
        self.args.vt_qemu_bin = None
        self.args.vt_dst_qemu_bin = None
        self.args.vt_nettype = 'user'
        self.args.vt_only_type_specific = False
        self.args.vt_tests = ''
        self.args.vt_connect_uri = 'qemu:///system'
        self.args.vt_accel = 'kvm'
        self.args.vt_monitor = 'human'
        self.args.vt_smp = 1
        self.args.vt_image_type = 'qcow2'
        self.args.vt_nic_model = 'virtio_net'
        self.args.vt_disk_bus = 'virtio_blk'
        self.args.vt_vhost = 'off'
        self.args.vt_malloc_perturb = 'yes'
        self.args.vt_qemu_sandbox = 'on'
        self.args.vt_tests = ''
        self.args.show_job_log = False
        self.args.test_lister = True


class VirtTestLoader(loader.TestLoader):

    def __init__(self, job=None, args=None):
        if job is None:
            job = VirtTestListJob(args=args)
        loader.TestLoader.__init__(self, job=job)
        standalone_test.reset_logging()
        if self.job.args.show_job_log:
            configure_console_logging()
        else:
            if job.logfile is not None:
                configure_file_logging(logfile=job.logfile)

    def _get_parser(self):
        options_processor = VirtTestOptionsProcess(self.job)
        return options_processor.get_parser()

    def get_extra_listing(self, args):
        if args.vt_list_guests:
            use_paginator = args.paginator == 'on'
            try:
                view = output.View(use_paginator=use_paginator)
                guest_listing(args, view)
            finally:
                view.cleanup()
            sys.exit(0)

    def get_base_keywords(self):
        """
        Get base keywords to use (when no keywords are passed to 'list').

        Used to list all tests available in virt-test.

        :return: list with keyword strings.
        """
        return ['vt_list_all']

    def get_type_label_mapping(self):
        """
        Get label mapping for display in test listing.

        :return: Dict {TestClass: 'TEST_LABEL_STRING'}
        """
        return {VirtTest: 'VT'}

    def get_decorator_mapping(self):
        """
        Get label mapping for display in test listing.

        :return: Dict {TestClass: decorator function}
        """
        term_support = output.TermSupport()
        return {VirtTest: term_support.healthy_str}

    def discover(self, params_list):
        """
        Discover tests for test suite.

        :param params_list: a list of test parameters.
        :type params_list: list
        :return: a test suite (a list of test factories).
        """
        test_suite = []
        for params in params_list:
            # We want avocado to inject params coming from its multiplexer into
            # the test params. This will allow users to access avocado params from
            # inside virt tests. This feature would only work if the virt test
            # in question is executed from inside avocado.
            params['avocado_mux_append'] = True
            test_name = params.get("_short_name_map_file")["subtests.cfg"]
            params['id'] = test_name
            test_parameters = {'name': test_name,
                               'base_logdir': self.job.logdir,
                               'params': params,
                               'job': self.job}
            test_suite.append((VirtTest, test_parameters))
        return test_suite

    def validate_ui(self, test_suite, ignore_missing=False,
                    ignore_not_test=False, ignore_broken_symlinks=False,
                    ignore_access_denied=False):
        return []

    def discover_url(self, url):
        cartesian_parser = self._get_parser()
        if url != 'vt_list_all':
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
        if options.vt_config:
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
        # Here we turn the data the multiplexer injected into the params and turn it
        # into an AvocadoParams object, that will allow users to access data from it.
        # Example: sleep_length = test.avocado_params.get('sleep_length', default=1)
        p = params.get('avocado_params', None)
        if p is not None:
            params, mux_entry = p[0], p[1]
        else:
            params, mux_entry = [], []
        self.avocado_params = multiplexer.AvocadoParams(params, self.name, self.tag,
                                                        mux_entry,
                                                        self.default_params)

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
        try:
            self._runTest()
        # This trick will give better reporting of virt tests
        # being executed into avocado (skips and errors will display correctly)
        except error.TestNAError, details:
            raise exceptions.TestNAError(details)
        except error.TestError, details:
            raise exceptions.TestError(details)

    def _runTest(self):
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
        # There are a few options from the original virt-test runner
        # that don't quite make sense for avocado (avocado implements a better version of the virt-test feature).
        # So let's just inject some values into options.
        self.options.vt_verbose = False
        self.options.vt_log_level = logging.DEBUG
        self.options.vt_console_level = logging.DEBUG
        self.options.vt_no_downloads = False
        self.options.vt_selinux_setup = False
        # These options can be done by using virt test scripts
        self.options.vt_list_tests = False
        self.options.vt_list_guests = False

        # Here we'll inject values from the config file. Doing this makes things configurable yet the number
        # of options is not overwhelming.
        # setup section
        self.options.vt_keep_image = settings.get_value('virt_test.setup', 'keep_image', key_type=bool)
        self.options.vt_keep_image_between_tests = settings.get_value('virt_test.setup', 'keep_image_between_tests',
                                                                      key_type=bool)
        self.options.vt_keep_guest_running = settings.get_value('virt_test.setup', 'keep_guest_running', key_type=bool)
        # common section
        self.options.vt_data_dir = settings.get_value('virt_test.common', 'data_dir', default=None)
        self.options.vt_type_specific = settings.get_value('virt_test.common', 'type_specific_only', key_type=bool)
        self.options.vt_mem = settings.get_value('virt_test.common', 'mem', key_type=int)
        self.options.vt_arch = settings.get_value('virt_test.common', 'arch', default=None)
        self.options.vt_machine_type = settings.get_value('virt_test.common', 'machine_type',
                                                          default=defaults.DEFAULT_MACHINE_TYPE)
        # qemu section
        self.options.vt_accel = settings.get_value('virt_test.qemu', 'accel', default='kvm')
        self.options.vt_nettype = settings.get_value('virt_test.qemu', 'nettype', default='user')
        self.options.vt_netdst = settings.get_value('virt_test.qemu', 'netdst', default='virbr0')
        self.options.vt_vhost = settings.get_value('virt_test.qemu', 'vhost', default='off')
        self.options.vt_monitor = settings.get_value('virt_test.qemu', 'monitor', default='human')
        self.options.vt_smp = settings.get_value('virt_test.qemu', 'smp', default='2')
        self.options.vt_image_type = settings.get_value('virt_test.qemu', 'image_type', default='qcow2')
        self.options.vt_nic_model = settings.get_value('virt_test.qemu', 'nic_model', default='virtio_net')
        self.options.vt_disk_bus = settings.get_value('virt_test.qemu', 'disk_bus', default='virtio_blk')
        self.options.vt_qemu_sandbox = settings.get_value('virt_test.qemu', 'sandbox', default='on')
        self.options.vt_qemu_defconfig = settings.get_value('virt_test.qemu', 'defconfig', default='yes')
        self.options.vt_malloc_perturb = settings.get_value('virt_test.qemu', 'malloc_perturb', default='yes')

        # libvirt section
        self.options.vt_install_guest = settings.get_value('virt_test.libvirt', 'install_guest', key_type=bool,
                                                           default=False)
        self.options.vt_remove_guest = settings.get_value('virt_test.libvirt', 'remove_guest', key_type=bool,
                                                          default=False)

        # debug section
        self.options.vt_no_cleanup = settings.get_value('virt_test.debug', 'no_cleanup', key_type=bool, default=False)

        self.view = job.view
        self.cartesian_parser = None

    def _process_qemu_bin(self):
        """
        Puts the value of the qemu bin option in the cartesian parser command.
        """
        if self.options.vt_config and self.options.vt_qemu_bin is None:
            logging.info("Config provided and no --vt-qemu-bin set. Not trying "
                         "to automatically set qemu bin.")
        else:
            (qemu_bin_path, qemu_img_path, qemu_io_path,
             qemu_dst_bin_path) = standalone_test.find_default_qemu_paths(self.options.vt_qemu_bin,
                                                                          self.options.vt_dst_qemu_bin)
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
        if self.options.vt_config and self.options.vt_qemu_bin is None:
            logging.info("Config provided and no --vt-qemu-bin set. Not trying "
                         "to automatically set qemu bin.")
        else:
            (_, qemu_img_path,
             _, _) = standalone_test.find_default_qemu_paths(self.options.vt_qemu_bin,
                                                             self.options.vt_dst_qemu_bin)
            self.cartesian_parser.assign("qemu_img_binary", qemu_img_path)

    def _process_qemu_accel(self):
        """
        Puts the value of the qemu bin option in the cartesian parser command.
        """
        if self.options.vt_accel == 'tcg':
            self.cartesian_parser.assign("disable_kvm", "yes")

    def _process_bridge_mode(self):
        if self.options.vt_nettype not in SUPPORTED_NET_TYPES:
            self.view.notify(event='error', msg="Invalid --vt-nettype option '%s'. Valid options are: (%s)" %
                             (self.options.vt_nettype, ", ".join(SUPPORTED_NET_TYPES)))
            sys.exit(1)
        if self.options.vt_nettype == 'bridge':
            if os.getuid() != 0:
                self.view.notify(event='error', msg="In order to use bridge, you need to be root, aborting...")
                sys.exit(1)
            self.cartesian_parser.assign("nettype", "bridge")
            self.cartesian_parser.assign("netdst", self.options.netdst)
        elif self.options.vt_nettype == 'user':
            self.cartesian_parser.assign("nettype", "user")
        elif self.options.vt_nettype == 'none':
            self.cartesian_parser.assign("nettype", "none")

    def _process_monitor(self):
        if self.options.vt_monitor == 'qmp':
            self.cartesian_parser.assign("monitors", "qmp1")
            self.cartesian_parser.assign("monitor_type_qmp1", "qmp")

    def _process_smp(self):
        if not self.options.vt_config:
            if self.options.vt_smp == '1':
                self.cartesian_parser.only_filter("up")
            elif self.options.vt_smp == '2':
                self.cartesian_parser.only_filter("smp2")
            else:
                try:
                    self.cartesian_parser.only_filter("up")
                    self.cartesian_parser.assign("smp", int(self.options.vt_smp))
                except ValueError:
                    self.view.notify(event='error', msg="Invalid option for smp: %s, aborting..." % self.options.vt_smp)
                    sys.exit(1)
        else:
            logging.info("Config provided, ignoring --vt-smp option")

    def _process_arch(self):
        if self.options.vt_arch is None:
            pass
        elif not self.options.vt_config:
            self.cartesian_parser.only_filter(self.options.vt_arch)
        else:
            logging.info("Config provided, ignoring --vt-arch option")

    def _process_machine_type(self):
        if not self.options.vt_config:
            if self.options.vt_machine_type is None:
                # TODO: this is x86-specific, instead we can get the default
                # arch from qemu binary and run on all supported machine types
                if self.options.vt_arch is None and self.options.vt_guest_os is None:
                    import virttest.defaults
                    self.cartesian_parser.only_filter(
                        virttest.defaults.DEFAULT_MACHINE_TYPE)
            else:
                self.cartesian_parser.only_filter(self.options.vt_machine_type)
        else:
            logging.info("Config provided, ignoring --vt-machine-type option")

    def _process_image_type(self):
        if not self.options.vt_config:
            if self.options.vt_image_type in SUPPORTED_IMAGE_TYPES:
                self.cartesian_parser.only_filter(self.options.vt_image_type)
            else:
                self.cartesian_parser.only_filter("raw")
                # The actual param name is image_format.
                self.cartesian_parser.assign("image_format",
                                             self.options.vt_image_type)
        else:
            logging.info("Config provided, ignoring --vt-image-type option")

    def _process_nic_model(self):
        if not self.options.vt_config:
            if self.options.vt_nic_model in SUPPORTED_NIC_MODELS:
                self.cartesian_parser.only_filter(self.options.vt_nic_model)
            else:
                self.cartesian_parser.only_filter("nic_custom")
                self.cartesian_parser.assign(
                    "nic_model", self.options.vt_nic_model)
        else:
            logging.info("Config provided, ignoring --vt-nic-model option")

    def _process_disk_buses(self):
        if not self.options.vt_config:
            if self.options.vt_disk_bus in SUPPORTED_DISK_BUSES:
                self.cartesian_parser.only_filter(self.options.vt_disk_bus)
            else:
                self.view.notify(event='error', msg=("Option %s is not in the list %s, aborting..." %
                                                     (self.options.vt_disk_bus, SUPPORTED_DISK_BUSES)))
                sys.exit(1)
        else:
            logging.info("Config provided, ignoring --vt-disk-bus option")

    def _process_vhost(self):
        if not self.options.vt_config:
            if self.options.vt_nettype == "bridge":
                if self.options.vt_vhost == "on":
                    self.cartesian_parser.assign("vhost", "on")
                elif self.options.vt_vhost == "force":
                    self.cartesian_parser.assign("netdev_extra_params",
                                                 '",vhostforce=on"')
                    self.cartesian_parser.assign("vhost", "on")
            else:
                if self.options.vt_vhost in ["on", "force"]:
                    self.view.notify(event='error', msg=("Nettype %s is incompatible with vhost %s, aborting..." %
                                                         (self.options.vt_nettype, self.options.vt_vhost)))
                    sys.exit(1)
        else:
            logging.info("Config provided, ignoring --vt-vhost option")

    def _process_qemu_sandbox(self):
        if not self.options.vt_config:
            if self.options.vt_qemu_sandbox == "off":
                self.cartesian_parser.assign("qemu_sandbox", "off")
        else:
            logging.info("Config provided, ignoring \"--vt-sandbox <on|off>\" option")

    def _process_qemu_defconfig(self):
        if not self.options.vt_config:
            if self.options.vt_qemu_defconfig == "no":
                self.cartesian_parser.assign("defconfig", "no")
        else:
            logging.info("Config provided, ignoring \"--defconfig <yes|no>\" option")

    def _process_malloc_perturb(self):
        self.cartesian_parser.assign("malloc_perturb",
                                     self.options.vt_malloc_perturb)

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
        if self.options.vt_connect_uri:
            driver_found = False
            for driver in SUPPORTED_LIBVIRT_DRIVERS:
                if self.options.vt_connect_uri.count(driver):
                    driver_found = True
                    self.cartesian_parser.only_filter(driver)
            if not driver_found:
                self.view.notify(event='error', msg="Unsupported uri: %s." % self.options.vt_connect_uri)
                sys.exit(1)
        else:
            self.cartesian_parser.only_filter("qemu")

    def _process_guest_os(self):
        if not self.options.vt_config:
            if len(standalone_test.get_guest_name_list(self.options)) == 0:
                self.view.notify(event='error', msg="Guest name %s is not on the known guest os list "
                                                    "(see --vt-list-guests), aborting..." % self.options.vt_guest_os)
                sys.exit(1)
            self.cartesian_parser.only_filter(
                self.options.vt_guest_os or defaults.DEFAULT_GUEST_OS)
        else:
            logging.info("Config provided, ignoring --vt-guest-os option")

    def _process_list(self):
        if self.options.vt_list_tests:
            standalone_test.print_test_list(self.options,
                                            self.cartesian_parser)
            sys.exit(0)
        if self.options.vt_list_guests:
            standalone_test.print_guest_list(self.options)
            sys.exit(0)

    def _process_tests(self):
        if not self.options.vt_config:
            if self.options.vt_type:
                if self.options.url and self.options.dropin:
                    self.view.notify(event='error', msg="Option --vt-tests and --vt-run-dropin can't be set at "
                                                        "the same time")
                    sys.exit(1)
                elif self.options.url:
                    tests = self.options.url
                    if self.options.vt_type == 'libvirt':
                        if self.options.install_guest:
                            tests.insert(0, LIBVIRT_INSTALL)
                        if self.options.vt_remove_guest:
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
                    if self.options.vt_type == 'qemu':
                        self.cartesian_parser.only_filter(QEMU_DEFAULT_SET)
                        self.cartesian_parser.no_filter("with_reboot")
                    elif self.options.vt_type == 'libvirt':
                        self.cartesian_parser.only_filter(LIBVIRT_DEFAULT_SET)
                    elif self.options.vt_type == 'lvsb':
                        self.cartesian_parser.only_filter(LVSB_DEFAULT_SET)
                    elif self.options.vt_type == 'openvswitch':
                        self.cartesian_parser.only_filter(OVS_DEFAULT_SET)
        else:
            logging.info("Config provided, ignoring --vt-tests option")

    def _process_restart_vm(self):
        if not self.options.vt_config:
            if not self.options.vt_keep_guest_running:
                self.cartesian_parser.assign("kill_vm", "yes")

    def _process_restore_image_between_tests(self):
        if not self.options.vt_config:
            if not self.options.vt_keep_image_between_tests:
                self.cartesian_parser.assign("restore_image", "yes")

    def _process_mem(self):
        self.cartesian_parser.assign("mem", self.options.vt_mem)

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
        if not self.options.vt_config:
            if self.options.vt_no_filter:
                no_filter = ", ".join(self.options.vt_no_filter.split(' '))
                self.cartesian_parser.no_filter(no_filter)

    def _process_only_type_specific(self):
        if not self.options.vt_config:
            if self.options.vt_type_specific:
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

        if (not self.options.vt_type) and (not self.options.vt_config):
            self.view.notify(event='error',
                             msg="No type (--vt-type) or config (--vt-config) options specified, aborting...")
            sys.exit(0)

        if self.options.vt_type:
            if self.options.vt_type not in SUPPORTED_TEST_TYPES:
                self.view.notify(event='error', msg="Invalid test type %s. Valid test types: %s. Aborting..." %
                                                    (self.options.vt_type, " ".join(SUPPORTED_TEST_TYPES)))
                sys.exit(1)

        if self.options.vt_data_dir:
            data_dir.set_backing_data_dir(self.options.vt_data_dir)

        self.cartesian_parser = cartesian_config.Parser(debug=False)

        if self.options.vt_config:
            cfg = os.path.abspath(self.options.vt_config)

        if not self.options.vt_config:
            cfg = data_dir.get_backend_cfg_path(self.options.vt_type, 'tests.cfg')

        self.cartesian_parser.parse_file(cfg)
        if self.options.vt_type != 'lvsb':
            self._process_general_options()

        if self.options.vt_type == 'qemu':
            self._process_qemu_specific_options()
        elif self.options.vt_type == 'lvsb':
            self._process_lvsb_specific_options()
        elif self.options.vt_type == 'openvswitch':
            self._process_qemu_specific_options()
        elif self.options.vt_type == 'libvirt':
            self._process_libvirt_specific_options()
        # List and tests have to be the last things to be processed
        self._process_list()
        # Tests won't be processed here. The code of the function will
        # be utilized elsewhere.
        # self._process_tests()

    def get_parser(self):
        self._process_options()
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

        try:
            qemu_bin_path = standalone_test.find_default_qemu_paths()[0]
        except ValueError:
            qemu_bin_path = "Could not find one"

        qemu_nw_msg = "QEMU network option (%s). " % ", ".join(SUPPORTED_NET_TYPES)
        qemu_nw_msg += "Default: user"

        vt_compat_group_setup = parser.runner.add_argument_group('Virt-Test compat layer - VM Setup options')
        vt_compat_group_common = parser.runner.add_argument_group('Virt-Test compat layer - Common options')
        vt_compat_group_qemu = parser.runner.add_argument_group('Virt-Test compat layer - QEMU options')
        vt_compat_group_libvirt = parser.runner.add_argument_group('Virt-Test compat layer - Libvirt options')

        current_run_setup = settings.get_value('virt_test.setup', 'run_setup', key_type=bool)

        vt_compat_group_setup.add_argument("--vt-setup", action="store_true",
                                           dest="vt_setup",
                                           default=current_run_setup,
                                           help="Run virt test setup actions (restore JeOS image from pristine). "
                                                "Current: %s" % current_run_setup)

        vt_compat_group_common.add_argument("--vt-config", action="store", dest="vt_config",
                                            help=("Explicitly choose a cartesian config. "
                                                  "When choosing this, some options will be "
                                                  "ignored (see options below)"))
        vt_compat_group_common.add_argument("--vt-type", action="store", dest="vt_type",
                                            help="Choose test type (%s). Default: qemu" %
                                                 ", ".join(SUPPORTED_TEST_TYPES),
                                            default='qemu')
        vt_compat_group_common.add_argument("--vt-guest-os", action="store", dest="vt_guest_os",
                                            default=None,
                                            help=("Select the guest OS to be used. "
                                                  "If --vt-config is provided, this will be ignored. "
                                                  "Default: %s" % defaults.DEFAULT_GUEST_OS))
        vt_compat_group_common.add_argument("--vt-no-filter", action="store", dest="vt_no_filter", default="",
                                            help=("List of space separated 'no' filters to be "
                                                  "passed to the config parser. If --vt-config is "
                                                  "provided, this will be ignored. Default: ''"))
        qemu_bin_path_current = settings.get_value('virt_test.qemu', 'qemu_bin',
                                                   default=qemu_bin_path)
        vt_compat_group_qemu.add_argument("--vt-qemu-bin", action="store", dest="vt_qemu_bin",
                                          default=None,
                                          help=("Path to a custom qemu binary to be tested. "
                                                "If --vt-config is provided and this flag is omitted, "
                                                "no attempt to set the qemu binaries will be made. "
                                                "Current: %s" % qemu_bin_path_current))
        qemu_dst_bin_path_current = settings.get_value('virt_test.qemu', 'qemu_dst_bin',
                                                       default=qemu_bin_path)
        vt_compat_group_qemu.add_argument("--vt-qemu-dst-bin", action="store", dest="vt_dst_qemu_bin",
                                          default=None,
                                          help=("Path to a custom qemu binary to be tested for "
                                                "the destination of a migration, overrides "
                                                "--vt-qemu-bin. "
                                                "If --vt-config is provided and this flag is omitted, "
                                                "no attempt to set the qemu binaries will be made. "
                                                "Current: %s" % qemu_dst_bin_path_current))
        connect_uri_current = settings.get_value('virt_test.libvirt', 'connect_uri', default=None)
        vt_compat_group_libvirt.add_argument("--vt-connect-uri", action="store", dest="vt_connect_uri",
                                             default=connect_uri_current,
                                             help="Choose test connect uri for libvirt (E.g: %s). Current: %s" %
                                                  (", ".join(SUPPORTED_LIBVIRT_URIS), connect_uri_current))

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
