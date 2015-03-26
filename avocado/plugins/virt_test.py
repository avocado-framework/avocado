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
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Avocado virt-test compatibility wrapper
"""

import os
import sys
import traceback
import signal
import logging

from avocado.plugins import plugin
from avocado.settings import settings
from avocado import job

virt_test_dir = settings.get_value('virt-test', 'test_suite_path')
sys.path.append(virt_test_dir)


_TEST_LOGGER = logging.getLogger()


class StreamProxy(object):

    """
    Mechanism to redirect a stream to a file, allowing the original stream to
    be restored later.
    """

    def __init__(self, filename='/dev/null', stream=sys.stdout):
        """
        Keep 2 streams to write to, and eventually switch.
        """
        self.terminal = stream
        if filename is None:
            self.log = stream
        else:
            self.log = open(filename, "a")
        self.redirect()

    def write(self, message):
        """
        Write to the current stream.
        """
        self.stream.write(message)

    def flush(self):
        """
        Flush the current stream.
        """
        self.stream.flush()

    def restore(self):
        """Restore original stream"""
        self.stream = self.terminal

    def redirect(self):
        """Redirect stream to log file"""
        self.stream = self.log


def _silence_stderr():
    """
    Points the stderr FD (2) to /dev/null, silencing it.
    """
    out_fd = os.open('/dev/null', os.O_WRONLY | os.O_CREAT)
    try:
        os.dup2(out_fd, 2)
    finally:
        os.close(out_fd)
    sys.stderr = os.fdopen(2, 'w')


def _handle_stdout(options):
    """
    Replace stdout with a proxy object.

    Depending on self.options.verbose, make proxy print to /dev/null, or
    original sys.stdout stream.
    """
    if not options.verbose:
        _silence_stderr()
        # Replace stdout with our proxy pointing to /dev/null
        sys.stdout = StreamProxy(filename="/dev/null", stream=sys.stdout)
    else:
        # Retain full stdout
        sys.stdout = StreamProxy(filename=None, stream=sys.stdout)


def _restore_stdout():
    """
    Restore stdout. Used to re-enable stdout on error paths.
    """
    try:
        sys.stdout.restore()
    except AttributeError:
        pass


def _import_autotest_modules():
    """
    Import the autotest modules.

    Two methods will be attempted:
    1) If $AUTOTEST_PATH is set, import the libraries from an autotest checkout
       at $AUTOTEST_PATH.
    2) Import the libraries system wide. For this to work, the
       autotest-framework package for the given distro must be installed.
    """
    autotest_dir = os.environ.get('AUTOTEST_PATH')
    if autotest_dir is not None:
        autotest_dir = os.path.abspath(autotest_dir)
        client_dir = os.path.join(autotest_dir, 'client')
        setup_modules_path = os.path.join(client_dir, 'setup_modules.py')
        import imp
        try:
            setup_modules = imp.load_source('autotest_setup_modules',
                                            setup_modules_path)
        except:
            print "Failed to import autotest modules from $AUTOTEST_PATH"
            print "Could not load Python module %s" % (setup_modules_path)
            sys.exit(1)
        setup_modules.setup(base_path=client_dir,
                            root_module_name="autotest.client")

    try:
        from autotest.client import setup_modules
    except ImportError:
        print "Couldn't import autotest.client module"
        if autotest_dir is None:
            print("Environment variable $AUTOTEST_PATH not set. "
                  "please set it to a path containing an autotest checkout")
            print("Or install autotest-framework for your distro")
        sys.exit(1)


def _find_default_qemu_paths(options_qemu=None, options_dst_qemu=None):
    qemu_bin_path = None
    from virttest import utils_misc

    if options_qemu:
        if not os.path.isfile(options_qemu):
            raise RuntimeError("Invalid qemu binary provided (%s)" %
                               options_qemu)
        qemu_bin_path = options_qemu
    else:
        try:
            qemu_bin_path = utils_misc.find_command('qemu-kvm')
        except ValueError:
            qemu_bin_path = utils_misc.find_command('kvm')

    if options_dst_qemu is not None:
        if not os.path.isfile(options_dst_qemu):
            raise RuntimeError("Invalid dst qemu binary provided (%s)" %
                               options_dst_qemu)
        qemu_dst_bin_path = options_dst_qemu
    else:
        qemu_dst_bin_path = None

    qemu_dirname = os.path.dirname(qemu_bin_path)
    qemu_img_path = os.path.join(qemu_dirname, 'qemu-img')
    qemu_io_path = os.path.join(qemu_dirname, 'qemu-io')

    if not os.path.exists(qemu_img_path):
        qemu_img_path = utils_misc.find_command('qemu-img')

    if not os.path.exists(qemu_io_path):
        qemu_io_path = utils_misc.find_command('qemu-io')

    return [qemu_bin_path, qemu_img_path, qemu_io_path, qemu_dst_bin_path]


SUPPORTED_LOG_LEVELS = [
    "debug", "info", "warning", "error", "critical"]

SUPPORTED_TEST_TYPES = [
    'qemu', 'libvirt', 'libguestfs', 'openvswitch', 'v2v', 'lvsb']

SUPPORTED_LIBVIRT_URIS = ['qemu:///system', 'lxc:///']

SUPPORTED_LIBVIRT_DRIVERS = ['qemu', 'lxc', 'xen']

SUPPORTED_IMAGE_TYPES = ['raw', 'qcow2', 'qed', 'vmdk']

SUPPORTED_DISK_BUSES = ['ide', 'scsi', 'virtio_blk', 'virtio_scsi', 'lsi_scsi',
                        'ahci', 'usb2', 'xenblk']

SUPPORTED_NIC_MODELS = ["virtio_net", "e1000", "rtl8139", "spapr-vlan"]

SUPPORTED_NET_TYPES = ["bridge", "user", "none"]


def variant_only_file(filename):
    """
    Parse file containing flat list of items to append on an 'only' filter
    """
    from virttest import data_dir
    result = []
    if not os.path.isabs(filename):
        fullpath = os.path.realpath(os.path.join(data_dir.get_root_dir(),
                                                 filename))
    for line in open(fullpath).readlines():
        line = line.strip()
        if line.startswith('#') or len(line) < 3:
            continue
        result.append(line)
    return ", ".join(result)


QEMU_DEFAULT_SET = "migrate..tcp, migrate..unix, migrate..exec, migrate..fd"
LIBVIRT_DEFAULT_SET = variant_only_file('backends/libvirt/cfg/default_tests')
LVSB_DEFAULT_SET = ("lvsb_date")
OVS_DEFAULT_SET = ("load_module, ovs_basic")
LIBVIRT_INSTALL = "unattended_install.import.import.default_install.aio_native"
LIBVIRT_REMOVE = "remove_guest.without_disk"


class VirtTestJob(job.Job):

    def _job_report(self, job_elapsed_time, n_tests, n_tests_skipped,
                    n_tests_failed):
        """
        Print to stdout and run log stats of our test job.

        :param job_elapsed_time: Time it took for the tests to execute.
        :param n_tests: Total Number of tests executed.
        :param n_tests_skipped: Total Number of tests skipped.
        """
        minutes, seconds = divmod(job_elapsed_time, 60)
        hours, minutes = divmod(minutes, 60)

        pretty_time = ""
        if hours:
            pretty_time += "%02d:" % hours
        if hours or minutes:
            pretty_time += "%02d:" % minutes
        pretty_time += "%02d" % seconds

        n_tests_passed = n_tests - n_tests_skipped - n_tests_failed
        success_rate = 0
        if n_tests - n_tests_skipped > 0:
            success_rate = ((float(n_tests_passed) /
                             float(n_tests - n_tests_skipped)) * 100)

        self.view.notify(event='message',
                         msg="PASS       : %d" % n_tests_passed)
        self.view.notify(event='message',
                         msg="FAIL       : %d" % n_tests_failed)
        if n_tests_skipped:
            self.view.notify(event='message',
                             msg="SKIP      : %d" % n_tests_skipped)

        total_time_str = "TIME       : %.2f s" % job_elapsed_time
        if hours or minutes:
            total_time_str += " (%s)" % pretty_time

        self.view.notify(event='message', msg=total_time_str)
        logging.info("Job total elapsed time: %.2f s", job_elapsed_time)

        logging.info("Tests passed: %d", n_tests_passed)
        logging.info("Tests failed: %d", n_tests_failed)
        if n_tests_skipped:
            logging.info("Tests skipped: %d", n_tests_skipped)
        logging.info("Success rate: %.2f %%", success_rate)

    def run(self, parser, options):
        from virttest import data_dir, version, storage, cartesian_config
        from virttest import standalone_test, utils_misc
        from autotest.client.shared import error
        import time

        self._setup_job_results()
        self._make_test_result()
        self._start_sysinfo()
        self.view.start_file_logging(self.logfile,
                                     self.loglevel,
                                     self.unique_id)
        _TEST_LOGGER.info('JOB ID: %s', self.unique_id)
        _TEST_LOGGER.info('')
        standalone_test.cleanup_env(parser, options)
        self._update_latest_link()

        self.view.notify(event='message', msg='JOB ID     : %s' % self.unique_id)
        self.view.notify(event='message', msg="JOB LOG    : %s" % self.logfile)

        last_index = -1

        d = parser.get_dicts().next()

        if not options.config:
            if not options.keep_image_between_tests:
                _TEST_LOGGER.debug("Creating first backup of guest image")
                qemu_img = storage.QemuImg(d, data_dir.get_data_dir(), "image")
                qemu_img.backup_image(d, data_dir.get_data_dir(), 'backup', True)
                _TEST_LOGGER.debug("")

        for line in standalone_test.get_cartesian_parser_details(
                parser).splitlines():
            _TEST_LOGGER.info(line)

        _TEST_LOGGER.info("Defined test set:")
        for count, dic in enumerate(parser.get_dicts()):
            shortname = d.get("_name_map_file")["subtests.cfg"]

            logging.info("Test %4d:  %s", count + 1, shortname)
            last_index += 1

        if last_index == -1:
            self.view.notify(event='error', msg=("No tests generated by "
                                                 "config file '%s'" %
                                                 parser.filename))
            self.view.notify(event='error', msg=("Please check the file for "
                                                 "errors (bad variable names, "
                                                 "wrong indentation)"))
            sys.exit(-1)
        _TEST_LOGGER.info("")

        n_tests = last_index + 1
        n_tests_failed = 0
        n_tests_skipped = 0
        self.view.notify(event='message', msg="TESTS      : %s" % n_tests)

        status_dct = {}
        failed = False
        # Add the parameter decide if setup host env in the test case
        # For some special tests we only setup host in the first and last case
        # When we need to setup host env we need the host_setup_flag as
        # follows:
        #    0(00): do nothing
        #    1(01): setup env
        #    2(10): cleanup env
        #    3(11): setup and cleanup env
        index = 0
        setup_flag = 1
        cleanup_flag = 2
        job_start_time = time.time()

        for dct in parser.get_dicts():
            cartesian_config.postfix_parse(dct)
            shortname = d.get("_short_name_map_file")["subtests.cfg"]

            if index == 0:
                if dct.get("host_setup_flag", None) is not None:
                    flag = int(dct["host_setup_flag"])
                    dct["host_setup_flag"] = flag | setup_flag
                else:
                    dct["host_setup_flag"] = setup_flag
            if index == last_index:
                if dct.get("host_setup_flag", None) is not None:
                    flag = int(dct["host_setup_flag"])
                    dct["host_setup_flag"] = flag | cleanup_flag
                else:
                    dct["host_setup_flag"] = cleanup_flag
            index += 1

            # Add kvm module status
            dct["kvm_default"] = utils_misc.get_module_params(
                dct.get("sysfs_dir", "/sys"), "kvm")

            if dct.get("skip") == "yes":
                continue

            dependencies_satisfied = True
            for dep in dct.get("dep"):
                for test_name in status_dct.keys():
                    if dep not in test_name:
                        continue

                    if not status_dct[test_name]:
                        dependencies_satisfied = False
                        break

            if options.uri:
                dct["connect_uri"] = options.uri

            pretty_index = "(%d/%d)" % (index, n_tests)

            t = standalone_test.Test(dct, options)
            self.view._log_ui_info(msg="%s %s:  " % (pretty_index, t.tag),
                                   skip_newline=True)

            if dependencies_satisfied:
                t.set_debugdir(self.logdir)
                try:
                    try:
                        t_begin = time.time()
                        t.start_file_logging()
                        current_status = t.run_once()
                        if current_status:
                            _TEST_LOGGER.info("PASS %s", t.tag)
                        else:
                            _TEST_LOGGER.info("FAIL %s", t.tag)
                        _TEST_LOGGER.info("")
                        t.stop_file_logging()
                    finally:
                        t_end = time.time()
                        t_elapsed = t_end - t_begin
                except error.TestError, reason:
                    n_tests_failed += 1
                    _TEST_LOGGER.info("ERROR %s -> %s: %s", t.tag,
                                      reason.__class__.__name__, reason)
                    _TEST_LOGGER.info("")
                    t.stop_file_logging()
                    self.view._log_ui_status_error(t_elapsed)
                    status_dct[dct.get("name")] = False
                    continue
                except error.TestNAError, reason:
                    n_tests_skipped += 1
                    _TEST_LOGGER.info("SKIP %s -> %s: %s", t.tag,
                                      reason.__class__.__name__, reason)
                    _TEST_LOGGER.info("")
                    t.stop_file_logging()
                    self.view._log_ui_status_skip(t_elapsed)
                    status_dct[dct.get("name")] = False
                    continue
                except error.TestWarn, reason:
                    _TEST_LOGGER.info("WARN %s -> %s: %s", t.tag,
                                      reason.__class__.__name__,
                                      reason)
                    _TEST_LOGGER.info("")
                    t.stop_file_logging()
                    self.view._log_ui_status_warn(t_elapsed)
                    status_dct[dct.get("name")] = True
                    continue
                except Exception, reason:
                    n_tests_failed += 1
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    logging.error("")
                    tb_info = traceback.format_exception(exc_type, exc_value,
                                                         exc_traceback.tb_next)
                    tb_info = "".join(tb_info)
                    for e_line in tb_info.splitlines():
                        _TEST_LOGGER.error(e_line)
                    _TEST_LOGGER.error("")
                    _TEST_LOGGER.error("FAIL %s -> %s: %s", t.tag,
                                       reason.__class__.__name__,
                                       reason)
                    _TEST_LOGGER.info("")
                    t.stop_file_logging()
                    current_status = False
            else:
                self.view._log_ui_status_skip(t_elapsed)
                status_dct[dct.get("name")] = False
                continue

            if not current_status:
                failed = True
                self.view._log_ui_status_fail(t_elapsed)

            else:
                self.view._log_ui_status_pass(t_elapsed)

            status_dct[dct.get("name")] = current_status

        standalone_test.cleanup_env(parser, options)

        job_end_time = time.time()
        job_elapsed_time = job_end_time - job_start_time
        self._job_report(job_elapsed_time, n_tests, n_tests_skipped,
                         n_tests_failed)

        return not failed


class VirtTestApp(object):

    """
    Class representing the execution of the virt test runner.
    """
    @staticmethod
    def system_setup():
        """
        Set up things that affect the whole process

        Initialize things that will affect the whole process, such as
        environment variables, setting up Python module paths, or redirecting
        stdout and/or stderr.
        """
        # workaround for a but in some Autotest versions, that call
        # logging.basicConfig() with DEBUG loglevel as soon as the modules
        # are imported
        logging.basicConfig(loglevel=logging.ERROR)
        _import_autotest_modules()

        # set English environment
        # (command output might be localized, need to be safe)
        os.environ['LANG'] = 'en_US.UTF-8'

    def __init__(self, args):
        """
        Parses options and initializes attributes.
        """
        self.system_setup()

        self.options = args
        self.cartesian_parser = None

    def _process_qemu_bin(self):
        """
        Puts the value of the qemu bin option in the cartesian parser command.
        """
        if self.options.config and self.options.qemu is None:
            logging.info("Config provided and no --qemu-bin set. Not trying "
                         "to automatically set qemu bin.")
        else:
            (qemu_bin_path, qemu_img_path, qemu_io_path,
             qemu_dst_bin_path) = _find_default_qemu_paths(self.options.qemu,
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
            logging.info("Config provided and no --qemu-bin set. Not trying "
                         "to automatically set qemu bin.")
        else:
            (_, qemu_img_path,
             _, _) = _find_default_qemu_paths(self.options.qemu,
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
            _restore_stdout()
            print("Invalid --nettype option '%s'. Valid options are: (%s)" %
                  (self.options.nettype, ", ".join(SUPPORTED_NET_TYPES)))
            sys.exit(1)
        if self.options.nettype == 'bridge':
            if os.getuid() != 0:
                _restore_stdout()
                print("In order to use bridge, you need to be root, "
                      "aborting...")
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
                    _restore_stdout()
                    print("Invalid option for smp: %s, aborting..." %
                          self.options.smp)
                    sys.exit(1)
        else:
            logging.info("Config provided, ignoring --smp option")

    def _process_arch(self):
        if self.options.arch is None:
            pass
        elif not self.options.config:
            self.cartesian_parser.only_filter(self.options.arch)
        else:
            logging.info("Config provided, ignoring --arch option")

    def _process_machine_type(self):
        if not self.options.config:
            if self.options.machine_type is None:
                # TODO: this is x86-specific, instead we can get the default
                # arch from qemu binary and run on all supported machine types
                if self.options.arch is None and self.options.guest_os is None:
                    import virttest.defaults
                    self.cartesian_parser.only_filter(virttest.defaults.DEFAULT_MACHINE_TYPE)
            else:
                self.cartesian_parser.only_filter(self.options.machine_type)
        else:
            logging.info("Config provided, ignoring --machine-type option")

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
            logging.info("Config provided, ignoring --image-type option")

    def _process_nic_model(self):
        if not self.options.config:
            if self.options.nic_model in SUPPORTED_NIC_MODELS:
                self.cartesian_parser.only_filter(self.options.nic_model)
            else:
                self.cartesian_parser.only_filter("nic_custom")
                self.cartesian_parser.assign(
                    "nic_model", self.options.nic_model)
        else:
            logging.info("Config provided, ignoring --nic-model option")

    def _process_disk_buses(self):
        if not self.options.config:
            if self.options.disk_bus in SUPPORTED_DISK_BUSES:
                self.cartesian_parser.only_filter(self.options.disk_bus)
            else:
                _restore_stdout()
                print("Option %s is not in the list %s, aborting..." %
                      (self.options.disk_bus, SUPPORTED_DISK_BUSES))
                sys.exit(1)
        else:
            logging.info("Config provided, ignoring --disk-bus option")

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
                    _restore_stdout()
                    print("Nettype %s is incompatible with vhost %s, "
                          "aborting..." %
                          (self.options.nettype, self.options.vhost))
                    sys.exit(1)
        else:
            logging.info("Config provided, ignoring --vhost option")

    def _process_qemu_sandbox(self):
        if not self.options.config:
            if self.options.qemu_sandbox == "off":
                self.cartesian_parser.assign("qemu_sandbox", "off")
        else:
            logging.info("Config provided, ignoring \"--sandbox <on|off>\" option")

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
                print("Not supported uri: %s." % self.options.uri)
                sys.exit(1)
        else:
            self.cartesian_parser.only_filter("qemu")

    def _process_guest_os(self):
        if not self.options.config:
            from virttest import standalone_test, defaults
            if len(standalone_test.get_guest_name_list(self.options)) == 0:
                _restore_stdout()
                print("Guest name %s is not on the known guest os list "
                      "(see --list-guests), aborting..." %
                      self.options.guest_os)
                sys.exit(1)
            self.cartesian_parser.only_filter(
                self.options.guest_os or defaults.DEFAULT_GUEST_OS)
        else:
            logging.info("Config provided, ignoring --guest-os option")

    def _process_list(self):
        from virttest import standalone_test
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
                if self.options.tests and self.options.dropin:
                    print("Option --tests and --run-dropin can't be set at "
                          "the same time")
                    sys.exit(1)
                elif self.options.tests:
                    tests = self.options.tests.split(" ")
                    if self.options.type == 'libvirt':
                        if self.options.install_guest:
                            tests.insert(0, LIBVIRT_INSTALL)
                        if self.options.remove_guest:
                            tests.append(LIBVIRT_REMOVE)
                    self.cartesian_parser.only_filter(", ".join(tests))
                elif self.options.dropin:
                    from virttest import data_dir
                    dropin_tests = os.listdir(os.path.join(data_dir.get_root_dir(), "dropin"))
                    if len(dropin_tests) <= 1:
                        _restore_stdout()
                        print("No drop in tests detected, aborting. "
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
            logging.info("Config provided, ignoring --tests option")

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
        from virttest import utils_misc
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
        from virttest import cartesian_config, standalone_test
        from virttest import data_dir, bootstrap, arch, defaults

        if (not self.options.type) and (not self.options.config):
            _restore_stdout()
            print("No type (-t) or config (-c) options specified, aborting...")
            sys.exit(1)

        if self.options.update_config:
            from autotest.client.shared import logging_manager
            from virttest import utils_misc
            _restore_stdout()
            logging_manager.configure_logging(utils_misc.VirtLoggingConfig(),
                                              verbose=True)
            test_dir = data_dir.get_backend_dir(self.options.type)
            shared_dir = os.path.join(data_dir.get_root_dir(), "shared")
            bootstrap.create_config_files(test_dir, shared_dir,
                                          interactive=False,
                                          force_update=True)
            bootstrap.create_subtests_cfg(self.options.type)
            bootstrap.create_guest_os_cfg(self.options.type)
            sys.exit(0)

        if self.options.bootstrap:
            _restore_stdout()
            check_modules = []
            online_docs_url = None
            interactive = True
            if self.options.type == "qemu":
                default_userspace_paths = ["/usr/bin/qemu-kvm", "/usr/bin/qemu-img"]
                check_modules = arch.get_kvm_module_list()
                online_docs_url = "https://github.com/autotest/virt-test/wiki/GetStarted"
            elif self.options.type == "libvirt":
                default_userspace_paths = ["/usr/bin/qemu-kvm", "/usr/bin/qemu-img"]
            elif self.options.type == "libguestfs":
                default_userspace_paths = ["/usr/bin/libguestfs-test-tool"]
            elif self.options.type == "lvsb":
                default_userspace_paths = ["/usr/bin/virt-sandbox"]
            elif self.options.type == "openvswitch":
                default_userspace_paths = ["/usr/bin/qemu-kvm", "/usr/bin/qemu-img"]
                check_modules = ["openvswitch"]
                online_docs_url = "https://github.com/autotest/autotest/wiki/OpenVSwitch"
            elif self.options.type == "v2v":
                default_userspace_paths = ["/usr/bin/virt-v2v"]

            if not self.options.config:
                restore_image = not(self.options.no_downloads or
                                    self.options.keep_image)
            else:
                restore_image = False

            test_dir = data_dir.get_backend_dir(self.options.type)
            bootstrap.bootstrap(test_name=self.options.type, test_dir=test_dir,
                                base_dir=data_dir.get_data_dir(),
                                default_userspace_paths=default_userspace_paths,
                                check_modules=check_modules,
                                online_docs_url=online_docs_url,
                                interactive=interactive,
                                selinux=self.options.selinux_setup,
                                restore_image=restore_image,
                                verbose=self.options.verbose,
                                update_providers=self.options.update_providers,
                                guest_os=(self.options.guest_os or
                                          defaults.DEFAULT_GUEST_OS))
            sys.exit(0)

        if self.options.type:
            if self.options.type not in SUPPORTED_TEST_TYPES:
                _restore_stdout()
                print("Invalid test type %s. Valid test types: %s. "
                      "Aborting..." % (self.options.type,
                                       " ".join(SUPPORTED_TEST_TYPES)))
                sys.exit(1)

        if self.options.log_level not in SUPPORTED_LOG_LEVELS:
            _restore_stdout()
            print("Invalid log level '%s'. Valid log levels: %s. "
                  "Aborting..." % (self.options.log_level,
                                   " ".join(SUPPORTED_LOG_LEVELS)))
            sys.exit(1)
        num_level = getattr(logging, self.options.log_level.upper(), None)
        self.options.log_level = num_level

        if self.options.console_level not in SUPPORTED_LOG_LEVELS:
            _restore_stdout()
            print("Invalid console level '%s'. Valid console levels: %s. "
                  "Aborting..." % (self.options.console_level,
                                   " ".join(SUPPORTED_LOG_LEVELS)))
            sys.exit(1)
        num_level_console = getattr(logging,
                                    self.options.console_level.upper(),
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
        self._process_tests()

    def main(self):
        """
        Main point of execution of the test runner.

        1) Handle stdout/err according to the options given.
        2) Import the autotest modules.
        3) Sets the console logging for tests.
        4) Runs the tests according to the options given.
        """
        _handle_stdout(self.options)
        try:
            from virttest import standalone_test, defaults

            self._process_options()
            standalone_test.reset_logging()
            standalone_test.configure_console_logging(
                loglevel=self.options.console_level)
            standalone_test.bootstrap_tests(self.options)
            jb = VirtTestJob()
            ok = jb.run(self.cartesian_parser, self.options)

        except KeyboardInterrupt:
            standalone_test.cleanup_env(self.cartesian_parser, self.options)
            pid = os.getpid()
            os.kill(pid, signal.SIGTERM)

        except StopIteration:
            _restore_stdout()
            print("Empty config set generated ")
            if self.options.type:
                print("Tests chosen: '%s'" % self.options.tests)
                print("Check that you typed the tests "
                      "names correctly, and double "
                      "check that tests show "
                      "in --list-tests for guest '%s'" %
                      (self.options.guest_os or defaults.DEFAULT_GUEST_OS))
                sys.exit(1)

            if self.options.config:
                print("Please check your custom config file %s" %
                      self.options.config)
                sys.exit(1)

        except Exception:
            _restore_stdout()
            print("Internal error, traceback follows...")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_info = traceback.format_exception(exc_type, exc_value,
                                                 exc_traceback.tb_next)
            tb_info = "".join(tb_info)
            for e_line in tb_info.splitlines():
                print(e_line)
            sys.exit(1)

        if not ok:
            sys.exit(1)


class VirtTestRunner(plugin.Plugin):

    """
    Implements the avocado 'vt-run' subcommand
    """

    name = 'virt_test_runner'
    enabled = True
    priority = 0

    def configure(self, parser):
        """
        Add the subparser for the run action.

        :param parser: Main test runner parser.
        """
        self.parser = parser.subcommands.add_parser(
            'vt-run',
            help='Run virt-test suite tests')
        from virttest import data_dir
        import virttest.defaults

        self.default_guest_os = virttest.defaults.DEFAULT_GUEST_OS

        try:
            qemu_bin_path = _find_default_qemu_paths()[0]
        except ValueError:
            qemu_bin_path = "Could not find one"

        if os.getuid() == 0:
            nettype_default = 'bridge'
        else:
            nettype_default = 'user'

        debug = self.parser.add_argument_group(self, 'Debug Options')
        debug.add_argument("-v", "--verbose", action="store_true",
                           dest="verbose", help=("Exhibit test "
                                                 "messages in the console "
                                                 "(used for debugging)"))
        debug.add_argument("--console-level", action="store",
                           dest="console_level",
                           default="debug",
                           help=("Log level of test messages in the console. Only valid "
                                 "with --verbose. "
                                 "Supported levels: " +
                                 ", ".join(SUPPORTED_LOG_LEVELS) +
                                 ". Default: "))
        debug.add_argument("--show-open-fd", action="store_true",
                           dest="show_open_fd", help=("Show how many "
                                                      "open fds at the end of "
                                                      "each test "
                                                      "(used for debugging)"))

        general = self.parser.add_argument_group(self, 'General Options')
        general.add_argument("-b", "--bootstrap", action="store_true",
                             dest="bootstrap", help=("Perform test suite setup "
                                                     "procedures, such as "
                                                     "downloading JeOS and check "
                                                     "required programs and "
                                                     "libs. Requires -t to be set"))
        general.add_argument("--update-config", action="store_true",
                             default=False,
                             dest="update_config", help=("Forces configuration "
                                                         "updates (all manual "
                                                         "config file editing "
                                                         "will be lost). "
                                                         "Requires -t to be set"))
        general.add_argument("--update-providers", action="store_true",
                             default=False,
                             dest="update_providers", help=("Forces test "
                                                            "providers to be "
                                                            "updated (git repos "
                                                            "will be pulled)"))
        general.add_argument("-t", "--type", action="store", dest="type",
                             help="Choose test type (%s)" %
                             ", ".join(SUPPORTED_TEST_TYPES))
        general.add_argument("--connect-uri", action="store", dest="uri",
                             help="Choose test connect uri for libvirt (E.g: %s)" %
                             ", ".join(SUPPORTED_LIBVIRT_URIS))
        general.add_argument("-c", "--config", action="store", dest="config",
                             help=("Explicitly choose a cartesian config. "
                                   "When choosing this, some options will be "
                                   "ignored"))
        general.add_argument("--no-downloads", action="store_true",
                             dest="no_downloads", default=False,
                             help="Do not attempt to download JeOS images")
        general.add_argument("--selinux-setup", action="store_true",
                             dest="selinux_setup", default=False,
                             help="Define default contexts of directory.")
        general.add_argument("-k", "--keep-image", action="store_true",
                             dest="keep_image",
                             help=("Don't restore the JeOS image from pristine "
                                   "at the beginning of the test suite run "
                                   "(faster but unsafe)"))
        general.add_argument("--keep-image-between-tests",
                             action="store_true", default=False,
                             dest="keep_image_between_tests",
                             help=("Don't restore the JeOS image from pristine "
                                   "between tests (faster but unsafe)"))
        general.add_argument("-g", "--guest-os", action="store", dest="guest_os",
                             default=None,
                             help=("Select the guest OS to be used. "
                                   "If -c is provided, this will be ignored. "
                                   "Default: %s" % self.default_guest_os))
        general.add_argument("--arch", action="store", dest="arch",
                             default=None,
                             help=("Architecture under test. "
                                   "If -c is provided, this will be ignored. "
                                   "Default: any that supports the given machine type"))
        general.add_argument(
            "--machine-type", action="store", dest="machine_type",
            default=None,
            help=("Machine type under test. "
                  "If -c is provided, this will be ignored. "
                  "Default: all for the chosen guests, %s if "
                  "--guest-os not given." % virttest.defaults.DEFAULT_MACHINE_TYPE))
        general.add_argument("--tests", action="store", dest="tests",
                             default="",
                             help=('List of space separated tests to be '
                                   'executed. '
                                   'If -c is provided, this will be ignored.'
                                   ' - example: --tests "boot reboot shutdown"'))
        general.add_argument("--list-tests", action="store_true", dest="list",
                             help="List tests available")
        general.add_argument("--list-guests", action="store_true",
                             dest="list_guests",
                             help="List guests available")
        general.add_argument("--logs-dir", action="store", dest="logdir",
                             help=("Path to the logs directory. "
                                   "Default path: %s" %
                                   os.path.join(data_dir.get_backing_data_dir(),
                                                'logs')))
        general.add_argument("--data-dir", action="store", dest="datadir",
                             help=("Path to a data dir. "
                                   "Default path: %s" %
                                   data_dir.get_backing_data_dir()))
        general.add_argument("--keep-guest-running", action="store_true",
                             dest="keep_guest_running", default=False,
                             help=("Don't shut down guests at the end of each "
                                   "test (faster but unsafe)"))
        general.add_argument("-m", "--mem", action="store", dest="mem",
                             default="1024",
                             help=("RAM dedicated to the main VM. Default:"
                                   ""))
        general.add_argument(
            "--no", action="store", dest="no_filter", default="",
            help=("List of space separated no filters to be "
                  "passed to the config parser. If -c is "
                  "provided, this will be ignored"))
        general.add_argument("--type-specific", action="store_true",
                             dest="only_type_specific", default=False,
                             help=("Enable only type specific tests. Shared"
                                   " tests will not be tested."))

        general.add_argument("--run-dropin", action="store_true", dest="dropin",
                             default=False,
                             help=("Run tests present on the drop in dir on the "
                                   "host. Incompatible with --tests."))

        general.add_argument("--log-level", action="store", dest="log_level",
                             default="debug",
                             help=("Set log level for top level log file."
                                   " Supported levels: " +
                                   ", ".join(SUPPORTED_LOG_LEVELS) +
                                   ". Default: "))

        general.add_argument("--no-cleanup", action="store_true",
                             dest="no_cleanup",
                             default=False,
                             help=("Don't clean up tmp files or VM processes at "
                                   "the end of a virt-test execution (useful "
                                   "for debugging)"))

        qemu = self.parser.add_argument_group(self, 'Options specific to the qemu test')
        qemu.add_argument("--qemu-bin", action="store", dest="qemu",
                          default=None,
                          help=("Path to a custom qemu binary to be tested. "
                                "If -c is provided and this flag is omitted, "
                                "no attempt to set the qemu binaries will be made. "
                                "Default path: %s" % qemu_bin_path))
        qemu.add_argument("--qemu-dst-bin", action="store", dest="dst_qemu",
                          default=None,
                          help=("Path to a custom qemu binary to be tested for "
                                "the destination of a migration, overrides "
                                "--qemu-bin. "
                                "If -c is provided and this flag is omitted, "
                                "no attempt to set the qemu binaries will be made. "
                                "Default path: %s" % qemu_bin_path))
        qemu.add_argument("--use-malloc-perturb", action="store",
                          dest="malloc_perturb", default="yes",
                          help=("Use MALLOC_PERTURB_ env variable set to 1 "
                                "to help catch memory allocation problems on "
                                "qemu (yes or no). Default: "))
        qemu.add_argument("--accel", action="store", dest="accel", default="kvm",
                          help=("Accelerator used to run qemu (kvm or tcg). "
                                "Default: kvm"))
        help_msg = "QEMU network option (%s). " % ", ".join(SUPPORTED_NET_TYPES)
        help_msg += "Default: "
        qemu.add_argument("--nettype", action="store", dest="nettype",
                          default=nettype_default, help=help_msg)
        qemu.add_argument("--netdst", action="store", dest="netdst",
                          default="virbr0",
                          help=("Bridge name to be used "
                                "(if you chose bridge as nettype). "
                                "Default: "))
        qemu.add_argument("--vhost", action="store", dest="vhost",
                          default="off",
                          help=("Whether to enable vhost for qemu "
                                "(on/off/force). Depends on nettype=bridge. "
                                "If -c is provided, this will be ignored. "
                                "Default: "))
        qemu.add_argument("--monitor", action="store", dest="monitor",
                          default='human',
                          help="Monitor type (human or qmp). Default: ")
        qemu.add_argument("--smp", action="store", dest="smp",
                          default='2',
                          help=("Number of virtual cpus to use. "
                                "If -c is provided, this will be ignored. "
                                "Default: "))
        qemu.add_argument("--image-type", action="store", dest="image_type",
                          default="qcow2",
                          help=("Image format type to use "
                                "(any valid qemu format). "
                                "If -c is provided, this will be ignored. "
                                "Default: "))
        qemu.add_argument("--nic-model", action="store", dest="nic_model",
                          default="virtio_net",
                          help=("Guest network card model. "
                                "If -c is provided, this will be ignored. "
                                "(any valid qemu format). Default: "))
        qemu.add_argument("--disk-bus", action="store", dest="disk_bus",
                          default="virtio_blk",
                          help=("Guest main image disk bus. One of " +
                                " ".join(SUPPORTED_DISK_BUSES) +
                                ". If -c is provided, this will be ignored. "
                                "Default: "))
        qemu.add_argument("--qemu_sandbox", action="store", dest="qemu_sandbox",
                          default="on",
                          help=("Enable qemu sandboxing "
                                "(on/off). Default: "))

        libvirt = self.parser.add_argument_group(self, 'Options specific to the libvirt test')
        libvirt.add_argument("--install", action="store_true",
                             dest="install_guest",
                             help=("Install the guest using import method before "
                                   "the tests are run."))
        libvirt.add_argument("--remove", action="store_true", dest="remove_guest",
                             help=("Remove the guest from libvirt. This will not "
                                   "delete the guest's disk file."))

        super(VirtTestRunner, self).configure(self.parser)

    def run(self, args):
        """
        Run test modules or simple tests.

        :param args: Command line args received from the run subparser.
        """
        app = VirtTestApp(args)
        app.main()
