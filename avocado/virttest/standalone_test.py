import os
import logging
import imp
import sys
import time
import traceback
import Queue
import glob
import shutil
from autotest.client.shared import error
from autotest.client import utils
import aexpect
import asset
import utils_misc
import utils_params
import utils_env
import utils_net
import env_process
import data_dir
import bootstrap
import storage
import cartesian_config
import arch
import funcatexit
import version
import qemu_vm
import defaults

global GUEST_NAME_LIST
GUEST_NAME_LIST = None
global TAG_INDEX
TAG_INDEX = {}


class Test(object):

    """
    Mininal test class used to run a virt test.
    """

    env_version = utils_env.get_env_version()

    def __init__(self, params, options):
        self.params = utils_params.Params(params)
        self.bindir = data_dir.get_root_dir()
        self.virtdir = os.path.join(self.bindir, 'shared')
        self.builddir = os.path.join(self.bindir, 'backends', params.get("vm_type"))

        self.srcdir = os.path.join(self.builddir, 'src')
        if not os.path.isdir(self.srcdir):
            os.makedirs(self.srcdir)

        self.tmpdir = os.path.join(self.bindir, 'tmp')
        if not os.path.isdir(self.tmpdir):
            os.makedirs(self.tmpdir)

        self.iteration = 0
        if options.config:
            self.tag = params.get("shortname")
        else:
            self.tag = params.get("_short_name_map_file")["subtests.cfg"]
        self.debugdir = None
        self.outputdir = None
        self.resultsdir = None
        self.logfile = None
        self.file_handler = None
        self.background_errors = Queue.Queue()

    def set_debugdir(self, debugdir):
        self.debugdir = os.path.join(debugdir, self.tag)
        self.outputdir = self.debugdir
        if not os.path.isdir(self.debugdir):
            os.makedirs(self.debugdir)
        self.resultsdir = os.path.join(self.debugdir, 'results')
        if not os.path.isdir(self.resultsdir):
            os.makedirs(self.resultsdir)
        self.profdir = os.path.join(self.resultsdir, 'profiling')
        if not os.path.isdir(self.profdir):
            os.makedirs(self.profdir)
        utils_misc.set_log_file_dir(self.debugdir)
        self.logfile = os.path.join(self.debugdir, 'debug.log')

    def write_test_keyval(self, d):
        utils.write_keyval(self.debugdir, d)

    def start_file_logging(self):
        self.file_handler = configure_file_logging(self.logfile)

    def stop_file_logging(self):
        logger = logging.getLogger()
        logger.removeHandler(self.file_handler)
        self.file_handler.close()

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

    def run_once(self):
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
        t_types = None
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
                                                  "exist" % (subtestdir))
                        subtest_dirs += data_dir.SubdirList(subtestdir,
                                                            bootstrap.test_filter)

                    provider = params.get("provider", None)

                    if provider is None:
                        # Verify if we have the correspondent source file for it
                        for generic_subdir in asset.get_test_provider_subdirs('generic'):
                            subtest_dirs += data_dir.SubdirList(generic_subdir,
                                                                bootstrap.test_filter)

                        for specific_subdir in asset.get_test_provider_subdirs(params.get("vm_type")):
                            subtest_dirs += data_dir.SubdirList(specific_subdir,
                                                                bootstrap.test_filter)
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
                    for t_type, test_module in test_modules.items():
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

                except Exception, e:
                    if (t_type is not None):
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


def print_stdout(sr, end=True):
    try:
        sys.stdout.restore()
    except AttributeError:
        pass
    if end:
        print(sr)
    else:
        print(sr),
    try:
        sys.stdout.redirect()
    except AttributeError:
        pass


class Bcolors(object):

    """
    Very simple class with color support.
    """

    def __init__(self):
        self.blue = '\033[94m'
        self.green = '\033[92m'
        self.yellow = '\033[93m'
        self.red = '\033[91m'
        self.end = '\033[0m'
        self.HEADER = self.blue
        self.PASS = self.green
        self.SKIP = self.yellow
        self.FAIL = self.red
        self.ERROR = self.red
        self.WARN = self.yellow
        self.ENDC = self.end
        allowed_terms = ['linux', 'xterm', 'xterm-256color', 'vt100',
                         'screen', 'screen-256color']
        term = os.environ.get("TERM")
        if (not os.isatty(1)) or (term not in allowed_terms):
            self.disable()

    def disable(self):
        self.blue = ''
        self.green = ''
        self.yellow = ''
        self.red = ''
        self.end = ''
        self.HEADER = ''
        self.PASS = ''
        self.SKIP = ''
        self.FAIL = ''
        self.ERROR = ''
        self.WARN = ''
        self.ENDC = ''

# Instantiate bcolors to be used in the functions below.
bcolors = Bcolors()


def print_header(sr):
    """
    Print a string to stdout with HEADER (blue) color.
    """
    print_stdout(bcolors.HEADER + sr + bcolors.ENDC)


def print_skip(open_fd=False):
    """
    Print SKIP to stdout with SKIP (yellow) color.
    """
    normal_skip_msg = bcolors.SKIP + "SKIP" + bcolors.ENDC
    fd_skip_msg = (bcolors.SKIP +
                   "SKIP (%s fd)" % utils_misc.get_virt_test_open_fds() +
                   bcolors.ENDC)
    if open_fd:
        msg = fd_skip_msg
    else:
        msg = normal_skip_msg

    print_stdout(msg)


def print_error(t_elapsed, open_fd=False):
    """
    Print ERROR to stdout with ERROR (red) color.
    """
    normal_error_msg = (bcolors.ERROR + "ERROR" +
                        bcolors.ENDC + " (%.2f s)" % t_elapsed)
    fd_error_msg = (bcolors.ERROR + "ERROR" +
                    bcolors.ENDC + " (%.2f s) (%s fd)" %
                    (t_elapsed, utils_misc.get_virt_test_open_fds()))
    if open_fd:
        msg = fd_error_msg
    else:
        msg = normal_error_msg

    print_stdout(msg)


def print_pass(t_elapsed, open_fd=False):
    """
    Print PASS to stdout with PASS (green) color.
    """
    normal_pass_msg = (bcolors.PASS + "PASS" +
                       bcolors.ENDC + " (%.2f s)" % t_elapsed)
    fd_pass_msg = (bcolors.PASS + "PASS" +
                   bcolors.ENDC + " (%.2f s) (%s fd)" %
                   (t_elapsed, utils_misc.get_virt_test_open_fds()))
    if open_fd:
        msg = fd_pass_msg
    else:
        msg = normal_pass_msg

    print_stdout(msg)


def print_fail(t_elapsed, open_fd=False):
    """
    Print FAIL to stdout with FAIL (red) color.
    """
    normal_fail_msg = (bcolors.FAIL + "FAIL" +
                       bcolors.ENDC + " (%.2f s)" % t_elapsed)
    fd_fail_msg = (bcolors.FAIL + "FAIL" +
                   bcolors.ENDC + " (%.2f s) (%s fd)" %
                   (t_elapsed, utils_misc.get_virt_test_open_fds()))
    if open_fd:
        msg = fd_fail_msg
    else:
        msg = normal_fail_msg

    print_stdout(msg)


def print_warn(t_elapsed, open_fd=False):
    """
    Print WARN to stdout with WARN (yellow) color.
    """
    normal_warn_msg = (bcolors.WARN + "WARN" +
                       bcolors.ENDC + " (%.2f s)" % t_elapsed)
    fd_warn_msg = (bcolors.WARN + "WARN" +
                   bcolors.ENDC + " (%.2f s) (%s fd)" %
                   (t_elapsed, utils_misc.get_virt_test_open_fds()))
    if open_fd:
        msg = fd_warn_msg
    else:
        msg = normal_warn_msg

    print_stdout(msg)


def reset_logging():
    """
    Remove all the handlers and unset the log level on the root logger.
    """
    logger = logging.getLogger()
    for hdlr in logger.handlers:
        logger.removeHandler(hdlr)
    logger.setLevel(logging.NOTSET)


def configure_console_logging(loglevel=logging.DEBUG):
    """
    Simple helper for adding a file logger to the root logger.
    """
    logger = logging.getLogger()
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(loglevel)

    fmt = '%(asctime)s %(levelname)-5.5s| %(message)s'
    formatter = logging.Formatter(fmt=fmt, datefmt='%H:%M:%S')

    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return stream_handler


def configure_file_logging(logfile, loglevel=logging.DEBUG):
    """
    Simple helper for adding a file logger to the root logger.
    """
    logger = logging.getLogger()
    file_handler = logging.FileHandler(filename=logfile)
    file_handler.setLevel(loglevel)

    fmt = '%(asctime)s %(levelname)-5.5s| %(message)s'
    formatter = logging.Formatter(fmt=fmt, datefmt='%H:%M:%S')

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return file_handler


def create_config_files(options):
    """
    Check if the appropriate configuration files are present.

    If the files are not present, create them.

    :param options: OptParser object with options.
    """
    shared_dir = os.path.dirname(data_dir.get_data_dir())
    test_dir = os.path.dirname(shared_dir)

    if (options.type and options.config):
        test_dir = data_dir.get_backend_dir(options.type)
    elif options.type:
        test_dir = data_dir.get_backend_dir(options.type)
    elif options.config:
        parent_config_dir = os.path.dirname(options.config)
        parent_config_dir = os.path.dirname(parent_config_dir)
        options.type = parent_config_dir
        test_dir = os.path.join(test_dir, parent_config_dir)

    if not os.path.exists(os.path.join(test_dir, "cfg")):
        print_stdout("Setup error: %s does not exist" %
                     os.path.join(test_dir, "cfg"))
        print_stdout("Perhaps you have not specified -t?")
        sys.exit(1)
    # lvsb test doesn't use shared configs
    if options.type != 'lvsb':
        bootstrap.create_config_files(test_dir, shared_dir, interactive=False)
        bootstrap.create_guest_os_cfg(options.type)
    bootstrap.create_subtests_cfg(options.type)


def get_paginator():
    try:
        less_cmd = utils_misc.find_command('less')
        return os.popen('%s -FRSX' % less_cmd, 'w')
    except ValueError:
        return sys.stdout


def get_cartesian_parser_details(cartesian_parser):
    """
    Print detailed information about filters applied to the cartesian cfg.

    :param cartesian_parser: Cartesian parser object.
    """
    details = ""
    details += ("Tests produced by config file %s\n\n" %
                cartesian_parser.filename)

    details += "The full test list was modified by the following:\n\n"

    if cartesian_parser.only_filters:
        details += "Filters applied:\n"
        for flt in cartesian_parser.only_filters:
            details += "    %s\n" % flt

    if cartesian_parser.no_filters:
        for flt in cartesian_parser.no_filters:
            details += "    %s\n" % flt

    details += "\n"
    details += "Different guest OS have different test lists\n"
    details += "\n"

    if cartesian_parser.assignments:
        details += "Assignments applied:\n"
        for flt in cartesian_parser.assignments:
            details += "    %s\n" % flt

    details += "\n"
    details += "Assignments override values previously set in the config file\n"
    details += "\n"

    return details


def print_test_list(options, cartesian_parser):
    """
    Helper function to pretty print the test list.

    This function uses a paginator, if possible (inspired on git).

    :param options: OptParse object with cmdline options.
    :param cartesian_parser: Cartesian parser object with test options.
    """
    pipe = get_paginator()
    index = 0

    pipe.write(get_cartesian_parser_details(cartesian_parser))
    for params in cartesian_parser.get_dicts():
        virt_test_type = params.get('virt_test_type', "")
        supported_virt_backends = virt_test_type.split(" ")
        if options.type in supported_virt_backends:
            index += 1
            shortname = params.get("_short_name_map_file")["subtests.cfg"]
            needs_root = ((params.get('requires_root', 'no') == 'yes')
                          or (params.get('vm_type') != 'qemu'))
            basic_out = (bcolors.blue + str(index) + bcolors.end + " " +
                         shortname)
            if needs_root:
                out = (basic_out + bcolors.yellow + " (requires root)" +
                       bcolors.end + "\n")
            else:
                out = basic_out + "\n"
            try:
                pipe.write(out)
            except IOError:
                return


def get_guest_name_parser(options):
    cartesian_parser = cartesian_config.Parser()
    machines_cfg_path = data_dir.get_backend_cfg_path(options.type,
                                                      'machines.cfg')
    guest_os_cfg_path = data_dir.get_backend_cfg_path(options.type,
                                                      'guest-os.cfg')
    cartesian_parser.parse_file(machines_cfg_path)
    cartesian_parser.parse_file(guest_os_cfg_path)
    if options.arch:
        cartesian_parser.only_filter(options.arch)
    if options.machine_type:
        cartesian_parser.only_filter(options.machine_type)
    if options.guest_os:
        cartesian_parser.only_filter(options.guest_os)
    return cartesian_parser


def get_guest_name_list(options):
    global GUEST_NAME_LIST
    if GUEST_NAME_LIST is None:
        guest_name_list = []
        for params in get_guest_name_parser(options).get_dicts():
            shortname = ".".join(params['name'].split(".")[1:])
            guest_name_list.append(shortname)

        GUEST_NAME_LIST = guest_name_list

    return GUEST_NAME_LIST


def print_guest_list(options):
    """
    Helper function to pretty print the guest list.

    This function uses a paginator, if possible (inspired on git).

    :param options: OptParse object with cmdline options.
    :param cartesian_parser: Cartesian parser object with test options.
    """
    pipe = get_paginator()
    # lvsb testing has no concept of guests
    if options.type == 'lvsb':
        pipe.write("No guest types available for lvsb testing")
        return
    index = 0
    pipe.write("Searched %s for guest images\n" %
               os.path.join(data_dir.get_data_dir(), 'images'))
    pipe.write("Available guests:")
    pipe.write("\n\n")
    for params in get_guest_name_parser(options).get_dicts():
        index += 1
        base_dir = params.get("images_base_dir", data_dir.get_data_dir())
        image_name = storage.get_image_filename(params, base_dir)
        name = params['name']
        if os.path.isfile(image_name):
            out = (bcolors.blue + str(index) + bcolors.end + " " +
                   name + "\n")
        else:
            out = (bcolors.blue + str(index) + bcolors.end + " " +
                   name + " " + bcolors.yellow +
                   "(missing %s)" % os.path.basename(image_name) +
                   bcolors.end + "\n")
        pipe.write(out)


def bootstrap_tests(options):
    """
    Bootstrap process (download the appropriate JeOS file to data dir).

    This function will check whether the JeOS is in the right location of the
    data dir, if not, it will download it non interactively.

    :param options: OptParse object with program command line options.
    """
    if options.type:
        test_dir = data_dir.get_backend_dir(options.type)
    elif options.config:
        parent_config_dir = os.path.dirname(os.path.dirname(options.config))
        parent_config_dir = os.path.dirname(parent_config_dir)
        options.type = parent_config_dir
        test_dir = os.path.abspath(parent_config_dir)

    if options.type == 'qemu':
        check_modules = arch.get_kvm_module_list()
    else:
        check_modules = None
    online_docs_url = "https://github.com/autotest/virt-test/wiki"

    if not options.config:
        restore_image = not options.keep_image
    else:
        restore_image = False

    os_info = defaults.get_default_guest_os_info()

    kwargs = {'test_name': options.type,
              'test_dir': test_dir,
              'base_dir': data_dir.get_data_dir(),
              'default_userspace_paths': None,
              'check_modules': check_modules,
              'online_docs_url': online_docs_url,
              'download_image': not options.no_downloads,
              'selinux': options.selinux_setup,
              'restore_image': restore_image,
              'interactive': False,
              'update_providers': options.update_providers,
              'guest_os': options.guest_os or os_info['variant']}

    # Tolerance we have without printing a message for the user to wait (3 s)
    tolerance = 3
    failed = False
    wait_message_printed = False

    bg = utils.InterruptedThread(bootstrap.bootstrap, kwargs=kwargs)
    t_begin = time.time()
    bg.start()

    while bg.isAlive():
        t_elapsed = time.time() - t_begin
        if t_elapsed > tolerance and not wait_message_printed:
            print_stdout("Running setup. Please wait...")
            wait_message_printed = True
            # if bootstrap takes too long, we temporarily make stdout verbose
            # again, so the user can see what's taking so long
            sys.stdout.restore()
        time.sleep(0.1)

    # in case stdout was restored above, redirect it again
    sys.stdout.redirect()

    reason = None
    try:
        bg.join()
    except Exception, e:
        failed = True
        reason = e

    t_end = time.time()
    t_elapsed = t_end - t_begin

    print_stdout(bcolors.HEADER + "SETUP:" + bcolors.ENDC, end=False)

    if not failed:
        print_pass(t_elapsed, open_fd=options.show_open_fd)
    else:
        print_fail(t_elapsed, open_fd=options.show_open_fd)
        print_stdout("Setup error: %s" % reason)
        sys.exit(-1)

    return True


def cleanup_env(parser, options):
    """
    Clean up virt-test temporary files.

    :param parser: Cartesian parser with run parameters.
    :param options: Test runner options object.
    """
    if options.no_cleanup:
        logging.info("Option --no-cleanup requested, not cleaning temporary "
                     "files and VM processes...")
        logging.info("")
    else:
        logging.info("Cleaning tmp files and VM processes...")
        d = parser.get_dicts().next()
        env_filename = os.path.join(data_dir.get_root_dir(),
                                    options.type, d.get("env", "env"))
        env = utils_env.Env(filename=env_filename, version=Test.env_version)
        env.destroy()
        # Kill all tail_threads which env constructor recreate.
        aexpect.kill_tail_threads()
        aexpect.clean_tmp_files()
        utils_net.clean_tmp_files()
        data_dir.clean_tmp_files()
        qemu_vm.clean_tmp_files()
        logging.info("")


def _job_report(job_elapsed_time, n_tests, n_tests_skipped, n_tests_failed):
    """
    Print to stdout and run log stats of our test job.

    :param job_elapsed_time: Time it took for the tests to execute.
    :param n_tests: Total Number of tests executed.
    :param n_tests_skipped: Total Number of tests skipped.
    :param n_tests_passed: Number of tests that passed.
    """
    minutes, seconds = divmod(job_elapsed_time, 60)
    hours, minutes = divmod(minutes, 60)

    pretty_time = ""
    if hours:
        pretty_time += "%02d:" % hours
    if hours or minutes:
        pretty_time += "%02d:" % minutes
    pretty_time += "%02d" % seconds

    total_time_str = "TOTAL TIME: %.2f s" % job_elapsed_time
    if hours or minutes:
        total_time_str += " (%s)" % pretty_time

    print_header(total_time_str)
    logging.info("Job total elapsed time: %.2f s", job_elapsed_time)

    n_tests_passed = n_tests - n_tests_skipped - n_tests_failed
    success_rate = 0
    if (n_tests - n_tests_skipped > 0):
        success_rate = ((float(n_tests_passed) /
                         float(n_tests - n_tests_skipped)) * 100)

    print_header("TESTS PASSED: %d" % n_tests_passed)
    print_header("TESTS FAILED: %d" % n_tests_failed)
    if n_tests_skipped:
        print_header("TESTS SKIPPED: %d" % n_tests_skipped)
    print_header("SUCCESS RATE: %.2f %%" % success_rate)

    logging.info("Tests passed: %d", n_tests_passed)
    logging.info("Tests failed: %d", n_tests_failed)
    if n_tests_skipped:
        logging.info("Tests skipped: %d", n_tests_skipped)
    logging.info("Success rate: %.2f %%", success_rate)


def run_tests(parser, options):
    """
    Runs the sequence of KVM tests based on the list of dctionaries
    generated by the configuration system, handling dependencies.

    :param parser: Config parser object.
    :param options: Test runner options object.
    :return: True, if all tests ran passed, False if any of them failed.
    """
    test_start_time = time.strftime('%Y-%m-%d-%H.%M.%S')
    logdir = options.logdir or os.path.join(data_dir.get_root_dir(), 'logs')
    debugbase = 'run-%s' % test_start_time
    debugdir = os.path.join(logdir, debugbase)
    latestdir = os.path.join(logdir, "latest")
    if not os.path.isdir(debugdir):
        os.makedirs(debugdir)
    try:
        os.unlink(latestdir)
    except OSError, detail:
        pass
    os.symlink(debugbase, latestdir)

    debuglog = os.path.join(debugdir, "debug.log")
    loglevel = options.log_level
    configure_file_logging(debuglog, loglevel)

    print_stdout(bcolors.HEADER +
                 "DATA DIR: %s" % data_dir.get_backing_data_dir() +
                 bcolors.ENDC)

    print_header("DEBUG LOG: %s" % debuglog)

    last_index = -1

    logging.info("Starting test job at %s", test_start_time)
    logging.info("")

    logging.info(version.get_pretty_version_info())
    logging.info("")

    cleanup_env(parser, options)

    d = parser.get_dicts().next()

    if not options.config:
        if not options.keep_image_between_tests:
            logging.debug("Creating first backup of guest image")
            qemu_img = storage.QemuImg(d, data_dir.get_data_dir(), "image")
            qemu_img.backup_image(d, data_dir.get_data_dir(), 'backup', True)
            logging.debug("")

    for line in get_cartesian_parser_details(parser).splitlines():
        logging.info(line)

    logging.info("Defined test set:")
    for i, d in enumerate(parser.get_dicts()):
        shortname = d.get("_name_map_file")["subtests.cfg"]

        logging.info("Test %4d:  %s", i + 1, shortname)
        last_index += 1

    if last_index == -1:
        print_stdout("No tests generated by config file %s" % parser.filename)
        print_stdout("Please check the file for errors (bad variable names, "
                     "wrong indentation)")
        sys.exit(-1)
    logging.info("")

    n_tests = last_index + 1
    n_tests_failed = 0
    n_tests_skipped = 0
    print_header("TESTS: %s" % n_tests)

    status_dct = {}
    failed = False
    # Add the parameter decide if setup host env in the test case
    # For some special tests we only setup host in the first and last case
    # When we need to setup host env we need the host_setup_flag as following:
    #    0(00): do nothing
    #    1(01): setup env
    #    2(10): cleanup env
    #    3(11): setup and cleanup env
    index = 0
    setup_flag = 1
    cleanup_flag = 2
    job_start_time = time.time()

    for dct in parser.get_dicts():
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

        current_status = False

        pretty_index = "(%d/%d)" % (index, n_tests)

        t = Test(dct, options)
        print_stdout("%s %s:" % (pretty_index, t.tag), end=False)

        if dependencies_satisfied:
            t.set_debugdir(debugdir)
            try:
                try:
                    t_begin = time.time()
                    t.start_file_logging()
                    current_status = t.run_once()
                    if current_status:
                        logging.info("PASS %s", t.tag)
                    else:
                        logging.info("FAIL %s", t.tag)
                    logging.info("")
                    t.stop_file_logging()
                finally:
                    t_end = time.time()
                    t_elapsed = t_end - t_begin
            except error.TestError, reason:
                n_tests_failed += 1
                logging.info("ERROR %s -> %s: %s", t.tag,
                             reason.__class__.__name__, reason)
                logging.info("")
                t.stop_file_logging()
                print_error(t_elapsed, open_fd=options.show_open_fd)
                status_dct[dct.get("name")] = False
                continue
            except error.TestNAError, reason:
                n_tests_skipped += 1
                logging.info("SKIP %s -> %s: %s", t.tag,
                             reason.__class__.__name__, reason)
                logging.info("")
                t.stop_file_logging()
                print_skip(open_fd=options.show_open_fd)
                status_dct[dct.get("name")] = False
                continue
            except error.TestWarn, reason:
                logging.info("WARN %s -> %s: %s", t.tag,
                             reason.__class__.__name__,
                             reason)
                logging.info("")
                t.stop_file_logging()
                print_warn(t_elapsed, open_fd=options.show_open_fd)
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
                    logging.error(e_line)
                logging.error("")
                logging.error("FAIL %s -> %s: %s", t.tag,
                              reason.__class__.__name__,
                              reason)
                logging.info("")
                t.stop_file_logging()
                current_status = False
        else:
            print_skip(open_fd=options.show_open_fd)
            status_dct[dct.get("name")] = False
            continue

        if not current_status:
            failed = True
            print_fail(t_elapsed, open_fd=options.show_open_fd)

        else:
            print_pass(t_elapsed, open_fd=options.show_open_fd)

        status_dct[dct.get("name")] = current_status

    cleanup_env(parser, options)

    job_end_time = time.time()
    job_elapsed_time = job_end_time - job_start_time
    _job_report(job_elapsed_time, n_tests, n_tests_skipped, n_tests_failed)

    return not failed
