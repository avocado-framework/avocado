"""
High-level virt test utility functions.

This module is meant to reduce code size by performing common test procedures.
Generally, code here should look like test code.

More specifically:
    - Functions in this module should raise exceptions if things go wrong
    - Functions in this module typically use functions and classes from
      lower-level modules (e.g. utils_misc, aexpect).
    - Functions in this module should not be used by lower-level modules.
    - Functions in this module should be used in the right context.
      For example, a function should not be used where it may display
      misleading or inaccurate info or debug messages.

:copyright: 2008-2013 Red Hat Inc.
"""

import commands
import errno
import glob
import imp
import locale
import logging
import os
import re
import signal
import tempfile
import threading
import time
import subprocess

from autotest.client import utils, os_dep
from autotest.client.shared import error
from autotest.client.tools import scan_results
from virttest import aexpect, remote, utils_misc, virt_vm, data_dir, utils_net
from virttest import storage, asset, bootstrap, remote
import virttest

import libvirt
import qemu
import libguestfs

try:
    from virttest.staging import utils_cgroup
except ImportError:
    # TODO: Obsoleted path used prior autotest-0.15.2/virttest-2013.06.24
    from autotest.client.shared import utils_cgroup

try:
    from virttest.staging import utils_memory
except ImportError:
    from autotest.client.shared import utils_memory

# Handle transition from autotest global_config (0.14.x series) to
# settings (0.15.x onwards)
try:
    # pylint: disable=E0611
    from autotest.client.shared import global_config
    section_values = global_config.global_config.get_section_values
    settings_value = global_config.global_config.get_config_value
except ImportError:
    from autotest.client.shared.settings import settings
    section_values = settings.get_section_values
    settings_value = settings.get_value


@error.context_aware
def update_boot_option(vm, args_removed=None, args_added=None,
                       need_reboot=True):
    """
    Update guest default kernel option.

    :param vm: The VM object.
    :param args_removed: Kernel options want to remove.
    :param args_added: Kernel options want to add.
    :param need_reboot: Whether need reboot VM or not.
    :raise error.TestError: Raised if fail to update guest kernel cmdlie.

    """
    if vm.params.get("os_type") == 'windows':
        # this function is only for linux, if we need to change
        # windows guest's boot option, we can use a function like:
        # update_win_bootloader(args_removed, args_added, reboot)
        # (this function is not implement.)
        # here we just:
        return

    login_timeout = int(vm.params.get("login_timeout"))
    session = vm.wait_for_login(timeout=login_timeout)

    msg = "Update guest kernel cmdline. "
    cmd = "grubby --update-kernel=`grubby --default-kernel` "
    if args_removed is not None:
        msg += " remove args: %s." % args_removed
        cmd += '--remove-args="%s." ' % args_removed
    if args_added is not None:
        msg += " add args: %s" % args_added
        cmd += '--args="%s"' % args_added
    error.context(msg, logging.info)
    s, o = session.cmd_status_output(cmd)
    if s != 0:
        logging.error(o)
        raise error.TestError("Fail to modify guest kernel cmdline")

    if need_reboot:
        error.context("Rebooting guest ...", logging.info)
        vm.reboot(session=session, timeout=login_timeout)


def stop_windows_service(session, service, timeout=120):
    """
    Stop a Windows service using sc.
    If the service is already stopped or is not installed, do nothing.

    :param service: The name of the service
    :param timeout: Time duration to wait for service to stop
    :raise error.TestError: Raised if the service can't be stopped
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        o = session.cmd_output("sc stop %s" % service, timeout=60)
        # FAILED 1060 means the service isn't installed.
        # FAILED 1062 means the service hasn't been started.
        if re.search(r"\bFAILED (1060|1062)\b", o, re.I):
            break
        time.sleep(1)
    else:
        raise error.TestError("Could not stop service '%s'" % service)


def start_windows_service(session, service, timeout=120):
    """
    Start a Windows service using sc.
    If the service is already running, do nothing.
    If the service isn't installed, fail.

    :param service: The name of the service
    :param timeout: Time duration to wait for service to start
    :raise error.TestError: Raised if the service can't be started
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        o = session.cmd_output("sc start %s" % service, timeout=60)
        # FAILED 1060 means the service isn't installed.
        if re.search(r"\bFAILED 1060\b", o, re.I):
            raise error.TestError("Could not start service '%s' "
                                  "(service not installed)" % service)
        # FAILED 1056 means the service is already running.
        if re.search(r"\bFAILED 1056\b", o, re.I):
            break
        time.sleep(1)
    else:
        raise error.TestError("Could not start service '%s'" % service)


def get_windows_file_abs_path(session, filename, extension="exe", tmout=240):
    """
    return file abs path "drive+path" by "wmic datafile"
    """
    cmd_tmp = "wmic datafile where \"Filename='%s' and "
    cmd_tmp += "extension='%s'\" get drive^,path"
    cmd = cmd_tmp % (filename, extension)
    info = session.cmd_output(cmd, timeout=tmout).strip()
    drive_path = re.search(r'(\w):\s+(\S+)', info, re.M)
    if not drive_path:
        raise error.TestError("Not found file %s.%s in your guest"
                              % (filename, extension))
    return ":".join(drive_path.groups())


def get_windows_disk_drive(session, filename, extension="exe", tmout=240):
    """
    Get the windows disk drive number
    """
    return get_windows_file_abs_path(session, filename,
                                     extension).split(":")[0]


def get_time(session, time_command, time_filter_re, time_format):
    """
    Return the host time and guest time.  If the guest time cannot be fetched
    a TestError exception is raised.

    Note that the shell session should be ready to receive commands
    (i.e. should "display" a command prompt and should be done with all
    previous commands).

    :param session: A shell session.
    :param time_command: Command to issue to get the current guest time.
    :param time_filter_re: Regex filter to apply on the output of
            time_command in order to get the current time.
    :param time_format: Format string to pass to time.strptime() with the
            result of the regex filter.
    :return: A tuple containing the host time and guest time.
    """
    if re.findall("ntpdate|w32tm", time_command):
        output = session.cmd(time_command)
        if re.match('ntpdate', time_command):
            try:
                offset = re.findall('offset (.*) sec', output)[0]
            except IndexError:
                msg = "Fail to get guest time offset. Command "
                msg += "'%s', output: %s" % (time_command, output)
                raise error.TestError(msg)
            try:
                host_main, host_mantissa = re.findall(time_filter_re, output)[0]
                host_time = (time.mktime(time.strptime(host_main, time_format)) +
                             float("0.%s" % host_mantissa))
            except Exception:
                msg = "Fail to get host time. Command '%s', " % time_command
                msg += "output: %s" % output
                raise error.TestError(msg)
            guest_time = host_time - float(offset)
        else:
            try:
                guest_time = re.findall(time_filter_re, output)[0]
            except IndexError:
                msg = "Fail to get guest time. Command '%s', " % time_command
                msg += "output: %s" % output
                raise error.TestError(msg)
            try:
                offset = re.findall("o:(.*)s", output)[0]
            except IndexError:
                msg = "Fail to get guest time offset. Command "
                msg += "'%s', output: %s" % (time_command, output)
                raise error.TestError(msg)
            if re.match('PM', guest_time):
                hour = re.findall('\d+ (\d+):', guest_time)[0]
                hour = str(int(hour) + 12)
                guest_time = re.sub('\d+\s\d+:', "\d+\s%s:" % hour,
                                    guest_time)[:-3]
            else:
                guest_time = guest_time[:-3]
            guest_time = time.mktime(time.strptime(guest_time, time_format))
            host_time = guest_time + float(offset)
    elif re.findall("hwclock", time_command):
        loc = locale.getlocale(locale.LC_TIME)
        # Get and parse host time
        host_time_out = utils.run(time_command).stdout
        host_time_out, diff = host_time_out.split("  ")
        try:
            try:
                locale.setlocale(locale.LC_TIME, "C")
                host_time = time.mktime(time.strptime(host_time_out, time_format))
                host_time += float(diff.split(" ")[0])
            except Exception, err:
                logging.debug("(time_format, time_string): (%s, %s)",
                              time_format, host_time_out)
                raise err
        finally:
            locale.setlocale(locale.LC_TIME, loc)

        output = session.cmd_output(time_command)

        # Get and parse guest time
        try:
            str_time = re.findall(time_filter_re, output)[0]
            str_time, diff = str_time.split("  ")
        except IndexError:
            logging.debug("The time string from guest is:\n%s", str_time)
            raise error.TestError("The time string from guest is unexpected.")
        except Exception, err:
            logging.debug("(time_filter_re, time_string): (%s, %s)",
                          time_filter_re, str_time)
            raise err

        guest_time = None
        try:
            try:
                locale.setlocale(locale.LC_TIME, "C")
                guest_time = time.mktime(time.strptime(str_time, time_format))
                guest_time += float(diff.split(" ")[0])
            except Exception, err:
                logging.debug("(time_format, time_string): (%s, %s)",
                              time_format, host_time_out)
                raise err
        finally:
            locale.setlocale(locale.LC_TIME, loc)
    else:
        host_time = time.time()
        output = session.cmd_output(time_command).strip()
        num = 0.0
        reo = None

        try:
            reo = re.findall(time_filter_re, output)[0]
            if len(reo) > 1:
                num = float(reo[1])
        except IndexError:
            logging.debug("The time string from guest is:\n%s", output)
            raise error.TestError("The time string from guest is unexpected.")
        except ValueError, err:
            logging.debug("Couldn't create float number from %s" % (reo[1]))
        except Exception, err:
            logging.debug("(time_filter_re, time_string): (%s, %s)",
                          time_filter_re, output)
            raise err

        guest_time = time.mktime(time.strptime(reo, time_format)) + num

    return (host_time, guest_time)


def get_memory_info(lvms):
    """
    Get memory information from host and guests in format:
    Host: memfree = XXXM; Guests memsh = {XXX,XXX,...}

    :params lvms: List of VM objects
    :return: String with memory info report
    """
    if not isinstance(lvms, list):
        raise error.TestError("Invalid list passed to get_stat: %s " % lvms)

    try:
        meminfo = "Host: memfree = "
        meminfo += str(int(utils_memory.freememtotal()) / 1024) + "M; "
        meminfo += "swapfree = "
        mf = int(utils_memory.read_from_meminfo("SwapFree")) / 1024
        meminfo += str(mf) + "M; "
    except Exception, e:
        raise error.TestFail("Could not fetch host free memory info, "
                             "reason: %s" % e)

    meminfo += "Guests memsh = {"
    for vm in lvms:
        shm = vm.get_shared_meminfo()
        if shm is None:
            raise error.TestError("Could not get shared meminfo from "
                                  "VM %s" % vm)
        meminfo += "%dM; " % shm
    meminfo = meminfo[0:-2] + "}"

    return meminfo


@error.context_aware
def run_image_copy(test, params, env):
    """
    Copy guest images from nfs server.
    1) Mount the NFS share directory
    2) Check the existence of source image
    3) If it exists, copy the image from NFS

    :param test: kvm test object
    :param params: Dictionary with the test parameters
    :param env: Dictionary with test environment.
    """
    vm = env.get_vm(params["main_vm"])
    if vm is not None:
        vm.destroy()

    src = params.get('images_good')
    asset_name = '%s' % (os.path.split(params['image_name'])[1])
    image = '%s.%s' % (params['image_name'], params['image_format'])
    dst_path = storage.get_image_filename(params, data_dir.get_data_dir())
    image_dir = os.path.dirname(dst_path)
    if params.get("rename_error_image", "no") == "yes":
        error_image = os.path.basename(params['image_name']) + "-error"
        error_image += '.' + params['image_format']
        error_dst_path = os.path.join(image_dir, error_image)
        mv_cmd = "/bin/mv %s %s" % (dst_path, error_dst_path)
        utils.system(mv_cmd, timeout=360, ignore_status=True)

    if src:
        mount_dest_dir = params.get('dst_dir', '/mnt/images')
        if not os.path.exists(mount_dest_dir):
            try:
                os.makedirs(mount_dest_dir)
            except OSError, err:
                logging.warning('mkdir %s error:\n%s', mount_dest_dir, err)

        if not os.path.exists(mount_dest_dir):
            raise error.TestError('Failed to create NFS share dir %s' %
                                  mount_dest_dir)

        error.context("Mount the NFS share directory")
        if not utils_misc.mount(src, mount_dest_dir, 'nfs', 'ro'):
            raise error.TestError('Could not mount NFS share %s to %s' %
                                  (src, mount_dest_dir))

        error.context("Check the existence of source image")
        src_path = '%s/%s.%s' % (mount_dest_dir, asset_name,
                                 params['image_format'])
        asset_info = virttest.asset.get_file_asset(asset_name, src_path,
                                                   dst_path)
        if asset_info is None:
            raise error.TestError('Could not find %s' % image)
    else:
        asset_info = virttest.asset.get_asset_info(asset_name)

    # Do not force extraction if integrity information is available
    if asset_info['sha1_url']:
        force = params.get("force_copy", "no") == "yes"
    else:
        force = params.get("force_copy", "yes") == "yes"

    try:
        error.context("Copy image '%s'" % image, logging.info)
        if utils.is_url(asset_info['url']):
            virttest.asset.download_file(asset_info, interactive=False,
                                         force=force)
        else:
            utils.get_file(asset_info['url'], asset_info['destination'])

    finally:
        sub_type = params.get("sub_type")
        if sub_type:
            error.context("Run sub test '%s'" % sub_type, logging.info)
            params['image_name'] += "-error"
            params['boot_once'] = "c"
            vm.create(params=params)
            virttest.utils_test.run_virt_sub_test(test, params, env,
                                                  params.get("sub_type"))


@error.context_aware
def run_file_transfer(test, params, env):
    """
    Transfer a file back and forth between host and guest.

    1) Boot up a VM.
    2) Create a large file by dd on host.
    3) Copy this file from host to guest.
    4) Copy this file from guest to host.
    5) Check if file transfers ended good.

    :param test: QEMU test object.
    :param params: Dictionary with the test parameters.
    :param env: Dictionary with test environment.
    """
    vm = env.get_vm(params["main_vm"])
    vm.verify_alive()
    login_timeout = int(params.get("login_timeout", 360))

    error.context("Login to guest", logging.info)
    session = vm.wait_for_login(timeout=login_timeout)

    dir_name = test.tmpdir
    transfer_timeout = int(params.get("transfer_timeout"))
    transfer_type = params.get("transfer_type")
    tmp_dir = params.get("tmp_dir", "/tmp/")
    clean_cmd = params.get("clean_cmd", "rm -f")
    filesize = int(params.get("filesize", 4000))
    count = int(filesize / 10)
    if count == 0:
        count = 1

    host_path = os.path.join(dir_name, "tmp-%s" %
                             utils_misc.generate_random_string(8))
    host_path2 = host_path + ".2"
    cmd = "dd if=/dev/zero of=%s bs=10M count=%d" % (host_path, count)
    guest_path = (tmp_dir + "file_transfer-%s" %
                  utils_misc.generate_random_string(8))

    try:
        error.context("Creating %dMB file on host" % filesize, logging.info)
        utils.run(cmd)

        if transfer_type != "remote":
            raise error.TestError("Unknown test file transfer mode %s" %
                                  transfer_type)

        error.context("Transferring file host -> guest,"
                      " timeout: %ss" % transfer_timeout, logging.info)
        t_begin = time.time()
        vm.copy_files_to(host_path, guest_path, timeout=transfer_timeout)
        t_end = time.time()
        throughput = filesize / (t_end - t_begin)
        logging.info("File transfer host -> guest succeed, "
                     "estimated throughput: %.2fMB/s", throughput)

        error.context("Transferring file guest -> host,"
                      " timeout: %ss" % transfer_timeout, logging.info)
        t_begin = time.time()
        vm.copy_files_from(guest_path, host_path2, timeout=transfer_timeout)
        t_end = time.time()
        throughput = filesize / (t_end - t_begin)
        logging.info("File transfer guest -> host succeed, "
                     "estimated throughput: %.2fMB/s", throughput)

        error.context("Compare md5sum between original file and"
                      " transferred file", logging.info)
        if (utils.hash_file(host_path, method="md5") !=
                utils.hash_file(host_path2, method="md5")):
            raise error.TestFail("File changed after transfer host -> guest "
                                 "and guest -> host")

    finally:
        logging.info('Cleaning temp file on guest')
        try:
            session.cmd("%s %s" % (clean_cmd, guest_path))
        except aexpect.ShellError, detail:
            logging.warn("Could not remove temp files in guest: '%s'", detail)

        logging.info('Cleaning temp files on host')
        try:
            os.remove(host_path)
            os.remove(host_path2)
        except OSError:
            pass
        session.close()


def run_autotest(vm, session, control_path, timeout,
                 outputdir, params, copy_only=False, control_args=None):
    """
    Run an autotest control file inside a guest (linux only utility).

    :param vm: VM object.
    :param session: A shell session on the VM provided.
    :param control_path: A path to an autotest control file.
    :param timeout: Timeout under which the autotest control file must complete.
    :param outputdir: Path on host where we should copy the guest autotest
            results to.
    :param copy_only: If copy_only is True, copy the autotest to guest and
            return the command which need to run test on guest, without
            executing it.
    :param control_args: The arguments for control file.

    The following params is used by the migration
    :param params: Test params used in the migration test
    """
    def copy_if_hash_differs(vm, local_path, remote_path):
        """
        Copy a file to a guest if it doesn't exist or if its MD5sum differs.

        :param vm: VM object.
        :param local_path: Local path.
        :param remote_path: Remote path.

        :return: Whether the hash differs (True) or not (False).
        """
        hash_differs = False
        local_hash = utils.hash_file(local_path)
        basename = os.path.basename(local_path)
        output = session.cmd_output("md5sum %s" % remote_path)
        if "such file" in output:
            remote_hash = "0"
        elif output:
            remote_hash = output.split()[0]
        else:
            logging.warning("MD5 check for remote path %s did not return.",
                            remote_path)
            # Let's be a little more lenient here and see if it wasn't a
            # temporary problem
            remote_hash = "0"
        if remote_hash != local_hash:
            hash_differs = True
            logging.debug("Copying %s to guest "
                          "(remote hash: %s, local hash:%s)",
                          basename, remote_hash, local_hash)
            vm.copy_files_to(local_path, remote_path)
        return hash_differs

    def extract(vm, remote_path, dest_dir):
        """
        Extract the autotest .tar.bz2 file on the guest, ensuring the final
        destination path will be dest_dir.

        :param vm: VM object
        :param remote_path: Remote file path
        :param dest_dir: Destination dir for the contents
        """
        basename = os.path.basename(remote_path)
        logging.debug("Extracting %s on VM %s", basename, vm.name)
        session.cmd("rm -rf %s" % dest_dir, timeout=240)
        dirname = os.path.dirname(remote_path)
        session.cmd("cd %s" % dirname)
        session.cmd("mkdir -p %s" % os.path.dirname(dest_dir))
        e_cmd = "tar xjvf %s -C %s" % (basename, os.path.dirname(dest_dir))
        output = session.cmd(e_cmd, timeout=240)
        autotest_dirname = ""
        for line in output.splitlines()[1:]:
            autotest_dirname = line.split("/")[0]
            break
        if autotest_dirname != os.path.basename(dest_dir):
            session.cmd("cd %s" % os.path.dirname(dest_dir))
            session.cmd("mv %s %s" %
                        (autotest_dirname, os.path.basename(dest_dir)))

    def get_last_guest_results_index():
        res_index = 0
        for subpath in os.listdir(outputdir):
            if re.search("guest_autotest_results\d+", subpath):
                res_index = max(res_index, int(re.search("guest_autotest_results(\d+)", subpath).group(1)))
        return res_index

    def get_results(base_results_dir):
        """
        Copy autotest results present on the guest back to the host.
        """
        logging.debug("Trying to copy autotest results from guest")
        res_index = get_last_guest_results_index()
        guest_results_dir = os.path.join(outputdir, "guest_autotest_results%s" % (res_index + 1))
        os.mkdir(guest_results_dir)
        # result info tarball to host result dir
        session = vm.wait_for_login(timeout=360)
        results_dir = "%s/results/default" % base_results_dir
        results_tarball = "/tmp/results.tgz"
        compress_cmd = "cd %s && " % results_dir
        compress_cmd += "tar cjvf %s ./*" % results_tarball
        compress_cmd += " --exclude=*core*"
        compress_cmd += " --exclude=*crash*"
        session.cmd(compress_cmd, timeout=600)
        vm.copy_files_from(results_tarball, guest_results_dir)
        # cleanup autotest subprocess which not terminated, change PWD to
        # avoid current connection kill by fuser command;
        clean_cmd = "cd /tmp && fuser -k %s" % results_dir
        session.sendline(clean_cmd)
        session.cmd("rm -f %s" % results_tarball, timeout=240)
        results_tarball = os.path.basename(results_tarball)
        results_tarball = os.path.join(guest_results_dir, results_tarball)
        uncompress_cmd = "tar xjvf %s -C %s" % (results_tarball,
                                                guest_results_dir)
        utils.run(uncompress_cmd)
        utils.run("rm -f %s" % results_tarball)

    def get_results_summary():
        """
        Get the status of the tests that were executed on the guest.
        NOTE: This function depends on the results copied to host by
              get_results() function, so call get_results() first.
        """
        res_index = get_last_guest_results_index()
        base_dir = os.path.join(outputdir, "guest_autotest_results%s" % res_index)
        status_paths = glob.glob(os.path.join(base_dir, "*/status"))
        # for control files that do not use job.run_test()
        status_no_job = os.path.join(base_dir, "status")
        if os.path.exists(status_no_job):
            status_paths.append(status_no_job)
        status_path = " ".join(status_paths)

        try:
            output = utils.system_output("cat %s" % status_path)
        except error.CmdError, e:
            logging.error("Error getting guest autotest status file: %s", e)
            return None

        try:
            results = scan_results.parse_results(output)
            # Report test results
            logging.info("Results (test, status, duration, info):")
            for result in results:
                logging.info("\t %s", str(result))
            return results
        except Exception, e:
            logging.error("Error processing guest autotest results: %s", e)
            return None

    def config_control(control_path, job_args=None):
        """
        Edit the control file to adapt the current environment.

        Replace CLIENTIP with guestip, and replace SERVERIP with hostip.
        Support to pass arguments for client jobs.
        For example:
            stress args: job.run_test('stress', args="...")
            so job_args can be {'args': "..."}, they should be arguments
            of this job.

        :return: Path of a temp file which contains the result of replacing.
        """
        pattern2repl_dict = {r'CLIENTIP': vm.get_address(),
                             r'SERVERIP': utils_net.get_host_ip_address(params)}
        control_file = open(control_path)
        lines = control_file.readlines()
        control_file.close()

        for pattern, repl in pattern2repl_dict.items():
            for index in range(len(lines)):
                line = lines[index]
                lines[index] = re.sub(pattern, repl, line)

        # Provided arguments need to be added
        if job_args is not None and type(job_args) is dict:
            newlines = []
            for index in range(len(lines)):
                line = lines[index]
                # Only job lines need to be configured now
                if re.search("job.run_test", line):
                    # Get job type
                    allargs = line.split('(')[1].split(',')
                    if len(allargs) > 1:
                        job_type = allargs[0]
                    elif len(allargs) == 1:
                        job_type = allargs[0].split(')')[0]
                    else:
                        job_type = ""
                    # Assemble job function
                    jobline = "job.run_test(%s" % job_type
                    for key, value in job_args.items():
                        jobline += ", %s='%s'" % (key, value)
                    jobline += ")\n"
                    newlines.append(jobline)
                    break   # No need following lines
                else:
                    # None of these lines' business
                    newlines.append(line)
            lines = newlines

        fd, temp_control_path = tempfile.mkstemp(prefix="control",
                                                 dir=data_dir.get_tmp_dir())
        os.close(fd)

        temp_control = open(temp_control_path, "w")
        temp_control.writelines(lines)
        temp_control.close()
        return temp_control_path

    migrate_background = params.get("migrate_background") == "yes"
    if migrate_background:
        mig_timeout = float(params.get("mig_timeout", "3600"))
        mig_protocol = params.get("migration_protocol", "tcp")

    compressed_autotest_path = "/tmp/autotest.tar.bz2"
    destination_autotest_path = "/usr/local/autotest"

    # To avoid problems, let's make the test use the current AUTODIR
    # (autotest client path) location
    from autotest.client import common
    autotest_path = os.path.dirname(common.__file__)
    autotest_local_path = os.path.join(autotest_path, 'autotest-local')
    single_dir_install = os.path.isfile(autotest_local_path)
    if not single_dir_install:
        autotest_local_path = os_dep.command('autotest-local')
    kernel_install_path = os.path.join(autotest_path, 'tests',
                                       'kernelinstall')
    kernel_install_present = os.path.isdir(kernel_install_path)

    autotest_basename = os.path.basename(autotest_path)
    autotest_parentdir = os.path.dirname(autotest_path)

    # tar the contents of bindir/autotest
    cmd = ("cd %s; tar cvjf %s %s/*" %
           (autotest_parentdir, compressed_autotest_path, autotest_basename))
    cmd += " --exclude=%s/results*" % autotest_basename
    cmd += " --exclude=%s/tmp" % autotest_basename
    cmd += " --exclude=%s/control*" % autotest_basename
    cmd += " --exclude=*.pyc"
    cmd += " --exclude=*.svn"
    cmd += " --exclude=*.git"
    cmd += " --exclude=%s/tests/virt/*" % autotest_basename
    utils.run(cmd)

    # Copy autotest.tar.bz2
    update = copy_if_hash_differs(vm, compressed_autotest_path,
                                  compressed_autotest_path)

    # Extract autotest.tar.bz2
    if update:
        extract(vm, compressed_autotest_path, destination_autotest_path)

    g_fd, g_path = tempfile.mkstemp(dir='/tmp/')
    aux_file = os.fdopen(g_fd, 'w')
    config = section_values(('CLIENT', 'COMMON'))
    config.set('CLIENT', 'output_dir', destination_autotest_path)
    config.set('COMMON', 'autotest_top_path', destination_autotest_path)
    destination_test_dir = os.path.join(destination_autotest_path, 'tests')
    config.set('COMMON', 'test_dir', destination_test_dir)
    destination_test_output_dir = os.path.join(destination_autotest_path,
                                               'results')
    config.set('COMMON', 'test_output_dir', destination_test_output_dir)
    config.write(aux_file)
    aux_file.close()
    global_config_guest = os.path.join(destination_autotest_path,
                                       'global_config.ini')
    vm.copy_files_to(g_path, global_config_guest)
    os.unlink(g_path)

    if not single_dir_install:
        vm.copy_files_to(autotest_local_path,
                         os.path.join(destination_autotest_path,
                                      'autotest-local'))

    # Support autotests that are in client-server model.
    server_control_path = None
    if os.path.isdir(control_path):
        server_control_path = os.path.join(control_path, "control.server")
        server_control_path = config_control(server_control_path)
        control_path = os.path.join(control_path, "control.client")
    # Edit control file and copy it to vm.
    if control_args is not None:
        job_args = {'args': control_args}
    else:
        job_args = None
    temp_control_path = config_control(control_path, job_args=job_args)
    vm.copy_files_to(temp_control_path,
                     os.path.join(destination_autotest_path, 'control'))

    # remove the temp control file.
    if os.path.exists(temp_control_path):
        os.remove(temp_control_path)

    if not kernel_install_present:
        kernel_install_dir = os.path.join(virttest.data_dir.get_root_dir(),
                                          "shared", "deps", "run_autotest",
                                          "kernel_install")
        kernel_install_dest = os.path.join(destination_autotest_path, 'tests',
                                           'kernelinstall')
        vm.copy_files_to(kernel_install_dir, kernel_install_dest)
        module_dir = os.path.dirname(virttest.__file__)
        utils_koji_file = os.path.join(module_dir, 'staging', 'utils_koji.py')
        vm.copy_files_to(utils_koji_file, kernel_install_dest)

    # Copy a non crippled boottool and make it executable
    boottool_path = os.path.join(virttest.data_dir.get_root_dir(),
                                 "shared", "deps", "run_autotest",
                                 "boottool.py")
    boottool_dest = '/usr/local/autotest/tools/boottool.py'
    vm.copy_files_to(boottool_path, boottool_dest)
    session.cmd("chmod +x %s" % boottool_dest)

    # Clean the environment.
    session.cmd("cd %s" % destination_autotest_path)
    try:
        session.cmd("rm -f control.state")
        session.cmd("rm -rf results/*")
        session.cmd("rm -rf tmp/*")
    except aexpect.ShellError:
        pass

    # Check copy_only.
    if copy_only:
        return ("%s/autotest-local --args=\"%s\" --verbose %s/control" %
                (destination_autotest_path, control_args,
                 destination_autotest_path))

    # Run the test
    logging.info("Running autotest control file %s on guest, timeout %ss",
                 os.path.basename(control_path), timeout)

    # Start a background job to run server process if needed.
    server_process = None
    if server_control_path:
        command = ("%s %s --verbose -t %s" % (autotest_local_path,
                                              server_control_path,
                                              os.path.basename(server_control_path)))
        server_process = aexpect.run_bg(command)

    try:
        bg = None
        try:
            logging.info("---------------- Test output ----------------")
            if migrate_background:
                mig_timeout = float(params.get("mig_timeout", "3600"))
                mig_protocol = params.get("migration_protocol", "tcp")

                bg = utils.InterruptedThread(session.cmd_output,
                                             kwargs={
                                                 'cmd': "./autotest-local "
                                                        "--args="
                                                        "\"%s\" control" %
                                                        (control_args),
                                                 'timeout': timeout,
                                                 'print_func': logging.info})

                bg.start()

                while bg.isAlive():
                    logging.info("Autotest job did not end, start a round of "
                                 "migration")
                    vm.migrate(timeout=mig_timeout, protocol=mig_protocol)
            else:
                if params.get("guest_autotest_verbosity", "yes") == "yes":
                    verbose = " --verbose"
                else:
                    verbose = ""
                session.cmd_output("./autotest-local --args=\"%s\"%s"
                                   " control" % (control_args, verbose),
                                   timeout=timeout,
                                   print_func=logging.info)
        finally:
            logging.info("------------- End of test output ------------")
            if migrate_background and bg:
                bg.join()
            # Do some cleanup work on host if test need a server.
            if server_process:
                if server_process.is_alive():
                    utils_misc.kill_process_tree(server_process.get_pid(),
                                                 signal.SIGINT)
                server_process.close()

                # Remove the result dir produced by server_process.
                server_result = os.path.join(autotest_path,
                                             "results",
                                             os.path.basename(server_control_path))
                if os.path.isdir(server_result):
                    utils.safe_rmdir(server_result)
                # Remove the control file for server.
                if os.path.exists(server_control_path):
                    os.remove(server_control_path)

    except aexpect.ShellTimeoutError:
        if vm.is_alive():
            get_results(destination_autotest_path)
            get_results_summary()
            raise error.TestError("Timeout elapsed while waiting for job to "
                                  "complete")
        else:
            raise error.TestError("Autotest job on guest failed "
                                  "(VM terminated during job)")
    except aexpect.ShellProcessTerminatedError:
        get_results(destination_autotest_path)
        raise error.TestError("Autotest job on guest failed "
                              "(Remote session terminated during job)")

    get_results(destination_autotest_path)
    results = get_results_summary()

    if results is not None:
        # Make a list of FAIL/ERROR/ABORT results (make sure FAIL results appear
        # before ERROR results, and ERROR results appear before ABORT results)
        bad_results = [r[0] for r in results if r[1] == "FAIL"]
        bad_results += [r[0] for r in results if r[1] == "ERROR"]
        bad_results += [r[0] for r in results if r[1] == "ABORT"]

    # Fail the test if necessary
    if not results:
        raise error.TestFail("Autotest control file run did not produce any "
                             "recognizable results")
    if bad_results:
        if len(bad_results) == 1:
            e_msg = ("Test %s failed during control file execution" %
                     bad_results[0])
        else:
            e_msg = ("Tests %s failed during control file execution" %
                     " ".join(bad_results))
        raise error.TestFail(e_msg)


def get_loss_ratio(output):
    """
    Get the packet loss ratio from the output of ping.

    :param output: Ping output.
    """
    try:
        return int(re.findall('(\d+)% packet loss', output)[0])
    except IndexError:
        logging.debug(output)
        return -1


def raw_ping(command, timeout, session, output_func):
    """
    Low-level ping command execution.

    :param command: Ping command.
    :param timeout: Timeout of the ping command.
    :param session: Local executon hint or session to execute the ping command.
    """
    if session is None:
        process = aexpect.run_bg(command, output_func=output_func,
                                 timeout=timeout)

        # Send SIGINT signal to notify the timeout of running ping process,
        # Because ping have the ability to catch the SIGINT signal so we can
        # always get the packet loss ratio even if timeout.
        if process.is_alive():
            utils_misc.kill_process_tree(process.get_pid(), signal.SIGINT)

        status = process.get_status()
        output = process.get_output()

        process.close()
        return status, output
    else:
        output = ""
        try:
            output = session.cmd_output(command, timeout=timeout,
                                        print_func=output_func)
        except aexpect.ShellTimeoutError:
            # Send ctrl+c (SIGINT) through ssh session
            session.send("\003")
            try:
                output2 = session.read_up_to_prompt(print_func=output_func)
                output += output2
            except aexpect.ExpectTimeoutError, e:
                output += e.output
                # We also need to use this session to query the return value
                session.send("\003")

        session.sendline(session.status_test_command)
        try:
            o2 = session.read_up_to_prompt()
        except aexpect.ExpectError:
            status = -1
        else:
            try:
                status = int(re.findall("\d+", o2)[0])
            except Exception:
                status = -1

        return status, output


def ping(dest=None, count=None, interval=None, interface=None,
         packetsize=None, ttl=None, hint=None, adaptive=False,
         broadcast=False, flood=False, timeout=0,
         output_func=logging.debug, session=None):
    """
    Wrapper of ping.

    :param dest: Destination address.
    :param count: Count of icmp packet.
    :param interval: Interval of two icmp echo request.
    :param interface: Specified interface of the source address.
    :param packetsize: Packet size of icmp.
    :param ttl: IP time to live.
    :param hint: Path mtu discovery hint.
    :param adaptive: Adaptive ping flag.
    :param broadcast: Broadcast ping flag.
    :param flood: Flood ping flag.
    :param timeout: Timeout for the ping command.
    :param output_func: Function used to log the result of ping.
    :param session: Local executon hint or session to execute the ping command.
    """
    command = "ping"
    if ":" in dest:
        command = "ping6"
    if dest is not None:
        command += " %s " % dest
    else:
        command += " localhost "
    if count is not None:
        command += " -c %s" % count
    if interval is not None:
        command += " -i %s" % interval
    if interface is not None:
        command += " -I %s" % interface
    else:
        if dest.upper().startswith("FE80"):
            err_msg = "Using ipv6 linklocal must assigne interface"
            raise error.TestNAError(err_msg)
    if packetsize is not None:
        command += " -s %s" % packetsize
    if ttl is not None:
        command += " -t %s" % ttl
    if hint is not None:
        command += " -M %s" % hint
    if adaptive:
        command += " -A"
    if broadcast:
        command += " -b"
    if flood:
        command += " -f -q"
        command = "sleep %s && kill -2 `pidof ping` & %s" % (timeout, command)
        output_func = None
        timeout += 1

    return raw_ping(command, timeout, session, output_func)


def run_virt_sub_test(test, params, env, sub_type=None, tag=None):
    """
    Call another test script in one test script.
    :param test:   Virt Test object.
    :param params: Dictionary with the test parameters.
    :param env:    Dictionary with test environment.
    :param sub_type: Type of called test script.
    :param tag:    Tag for get the sub_test params
    """
    if sub_type is None:
        raise error.TestError("Unspecified sub test type. Please specify a"
                              "sub test type")

    provider = params.get("provider", None)
    subtest_dirs = []
    subtest_dir = None

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

    for d in subtest_dirs:
        module_path = os.path.join(d, "%s.py" % sub_type)
        if os.path.isfile(module_path):
            subtest_dir = d
            break

    if subtest_dir is None:
        raise error.TestError("Could not find test file %s.py "
                              "on directories %s" % (sub_type, subtest_dirs))

    f, p, d = imp.find_module(sub_type, [subtest_dir])
    test_module = imp.load_module(sub_type, f, p, d)
    f.close()
    # Run the test function
    run_func = utils_misc.get_test_entrypoint_func(sub_type, test_module)
    if tag is not None:
        params = params.object_params(tag)
    run_func(test, params, env)


def get_readable_cdroms(params, session):
    """
    Get the cdrom list which contain media in guest.

    :param params: Dictionary with the test parameters.
    :param session: A shell session on the VM provided.
    """
    get_cdrom_cmd = params.get("cdrom_get_cdrom_cmd")
    check_cdrom_patttern = params.get("cdrom_check_cdrom_pattern")
    o = session.get_command_output(get_cdrom_cmd)
    cdrom_list = re.findall(check_cdrom_patttern, o)
    logging.debug("Found cdroms on guest: %s" % cdrom_list)

    readable_cdroms = []
    test_cmd = params.get("cdrom_test_cmd")
    for d in cdrom_list:
        s, o = session.cmd_status_output(test_cmd % d)
        if s == 0:
            readable_cdroms.append(d)
            break

    if readable_cdroms:
        return readable_cdroms

    raise error.TestFail("Could not find a cdrom device with media inserted")


def service_setup(vm, session, directory):

    params = vm.get_params()
    rh_perf_envsetup_script = params.get("rh_perf_envsetup_script")
    rebooted = params.get("rebooted", "rebooted")

    if rh_perf_envsetup_script:
        src = os.path.join(directory, rh_perf_envsetup_script)
        vm.copy_files_to(src, "/tmp/rh_perf_envsetup.sh")
        logging.info("setup perf environment for host")
        commands.getoutput("bash %s host %s" % (src, rebooted))
        logging.info("setup perf environment for guest")
        session.cmd("bash /tmp/rh_perf_envsetup.sh guest %s" % rebooted)


def summary_up_result(result_file, ignore, row_head, column_mark):
    """
    Use to summary the monitor or other kinds of results. Now it calculates
    the average value for each item in the results. It fits to the records
    that are in matrix form.

    @result_file: files which need to calculate
    @ignore: pattern for the comment in results which need to through away
    @row_head: pattern for the items in row
    @column_mark: pattern for the first line in matrix which used to generate
    the items in column
    :return: A dictionary with the average value of results
    """
    head_flag = False
    result_dict = {}
    column_list = {}
    row_list = []
    fd = open(result_file, "r")
    for eachLine in fd:
        if len(re.findall(ignore, eachLine)) == 0:
            if len(re.findall(column_mark, eachLine)) != 0 and not head_flag:
                column = 0
                _, row, eachLine = re.split(row_head, eachLine)
                for i in re.split("\s+", eachLine):
                    if i:
                        result_dict[i] = {}
                        column_list[column] = i
                        column += 1
                head_flag = True
            elif len(re.findall(column_mark, eachLine)) == 0:
                column = 0
                _, row, eachLine = re.split(row_head, eachLine)
                row_flag = False
                for i in row_list:
                    if row == i:
                        row_flag = True
                if row_flag is False:
                    row_list.append(row)
                    for i in result_dict:
                        result_dict[i][row] = []
                for i in re.split("\s+", eachLine):
                    if i:
                        result_dict[column_list[column]][row].append(i)
                        column += 1
    fd.close()
    # Calculate the average value
    average_list = {}
    for i in column_list:
        average_list[column_list[i]] = {}
        for j in row_list:
            average_list[column_list[i]][j] = {}
            check = result_dict[column_list[i]][j][0]
            if utils_misc.aton(check) or utils_misc.aton(check) == 0.0:
                count = 0
                for k in result_dict[column_list[i]][j]:
                    count += utils_misc.aton(k)
                average_list[column_list[i]][j] = "%.2f" % (count /
                                                            len(result_dict[column_list[i]][j]))

    return average_list


def get_driver_hardware_id(driver_path, mount_point="/tmp/mnt-virtio",
                           storage_path="/tmp/prewhql.iso",
                           re_hw_id="(PCI.{14,50})", run_cmd=True):
    """
    Get windows driver's hardware id from inf files.

    :param dirver: Configurable driver name.
    :param mount_point: Mount point for the driver storage
    :param storage_path: The path of the virtio driver storage
    :param re_hw_id: the pattern for getting hardware id from inf files
    :param run_cmd:  Use hardware id in windows cmd command or not

    :return: Windows driver's hardware id
    """
    if not os.path.exists(mount_point):
        os.mkdir(mount_point)

    if not os.path.ismount(mount_point):
        utils.system("mount %s %s -o loop" % (storage_path, mount_point),
                     timeout=60)
    driver_link = os.path.join(mount_point, driver_path)
    txt_file = ""
    try:
        txt_file = open(driver_link, "r")
        txt = txt_file.read()
        hwid = re.findall(re_hw_id, txt)[-1].rstrip()
        if run_cmd:
            hwid = '^&'.join(hwid.split('&'))
        txt_file.close()
        utils.system("umount %s" % mount_point)
        return hwid
    except Exception, e:
        logging.error("Fail to get hardware id with exception: %s" % e)
        if txt_file:
            txt_file.close()
        utils.system("umount %s" % mount_point, ignore_status=True)
        return ""


class BackgroundTest(object):

    """
    This class would run a test in background through a dedicated thread.
    """

    def __init__(self, func, params, kwargs={}):
        """
        Initialize the object and set a few attributes.
        """
        self.thread = threading.Thread(target=self.launch,
                                       args=(func, params, kwargs))
        self.exception = None

    def launch(self, func, params, kwargs):
        """
        Catch and record the exception.
        """
        try:
            func(*params, **kwargs)
        except Exception, e:
            self.exception = e

    def start(self):
        """
        Run func(params) in a dedicated thread
        """
        self.thread.start()

    def join(self, timeout=600, ignore_status=False):
        """
        Wait for the join of thread and raise its exception if any.
        """
        self.thread.join(timeout)
        # pylint: disable=E0702
        if self.exception and (not ignore_status):
            raise self.exception

    def is_alive(self):
        """
        Check whether the test is still alive.
        """
        return self.thread.isAlive()


def get_image_info(image_file):
    return utils_misc.get_image_info(image_file)


def ntpdate(service_ip, session=None):
    """
    set the date and time via NTP
    """
    try:
        ntpdate_cmd = "ntpdate %s" % service_ip
        if session:
            session.cmd(ntpdate_cmd)
        else:
            utils.run(ntpdate_cmd)
    except (error.CmdError, aexpect.ShellError), detail:
        raise error.TestFail("Failed to set the date and time. %s" % detail)


def get_date(session=None):
    """
    Get the date time
    """
    try:
        date_cmd = "date +%s"
        if session:
            date_info = session.cmd_output(date_cmd).strip()
        else:
            date_info = utils.run(date_cmd).stdout.strip()
        return date_info
    except (error.CmdError, aexpect.ShellError), detail:
        raise error.TestFail("Get date failed. %s " % detail)


##########Stress functions################
class StressError(Exception):
    pass


class VMStress(object):

    """
    Run Stress tool in vms, such as stress, unixbench, iozone and etc.
    """

    def __init__(self, vm, stress_type):
        """
        Set parameters for stress type
        """

        def _parameters_filter(stress_type):
            """Set parameters according stress_type"""
            _control_files = {'unixbench': "unixbench5.control",
                              'stress': "stress.control"}
            _check_cmds = {'unixbench': "pidof -s ./Run",
                           'stress': "pidof -s stress"}
            _stop_cmds = {'unixbench': "killall ./Run",
                          'stress': "killall stress"}
            try:
                control_file = _control_files[stress_type]
                self.control_path = os.path.join(data_dir.get_root_dir(),
                                                 "shared/control",
                                                 control_file)
                self.check_cmd = _check_cmds[stress_type]
                self.stop_cmd = _stop_cmds[stress_type]
            except KeyError:
                self.control_path = ""
                self.check_cmd = ""
                self.stop_cmd = ""

        self.vm = vm
        self.params = vm.params
        self.timeout = 60
        self.stress_type = stress_type
        if stress_type not in ["stress", "unixbench"]:
            raise StressError("Stress %s is not supported now." % stress_type)

        _parameters_filter(stress_type)
        self.stress_args = self.params.get("stress_args", "")

    def get_session(self):
        try:
            session = self.vm.wait_for_login()
            return session
        except aexpect.ShellError, detail:
            raise StressError("Login %s failed:\n%s", self.vm.name, detail)

    @error.context_aware
    def load_stress_tool(self):
        """
        load stress tool in guest
        """
        session = self.get_session()
        command = run_autotest(self.vm, session, self.control_path,
                               None, None, self.params, copy_only=True,
                               control_args=self.stress_args)
        session.cmd("%s &" % command)
        logging.info("Command: %s", command)
        running = utils_misc.wait_for(self.app_running, first=0.5, timeout=60)
        if not running:
            raise StressError("Stress tool %s isn't running"
                              % self.stress_type)

    @error.context_aware
    def unload_stress(self):
        """
        stop stress tool manually
        """
        def _unload_stress():
            session = self.get_session()
            session.sendline(self.stop_cmd)
            if not self.app_running():
                return True
            return False

        error.context("stop stress app in guest", logging.info)
        utils_misc.wait_for(_unload_stress, first=2.0,
                            text="wait stress app quit", step=1.0, timeout=60)

    def app_running(self):
        """
        check whether app really run in background
        """
        session = self.get_session()
        status = session.cmd_status(self.check_cmd, timeout=60)
        return status == 0


class HostStress(object):

    """
    Run Stress tool on host, such as stress, unixbench, iozone and etc.
    """

    def __init__(self, params, stress_type):
        """
        Set parameters for stress type
        """

        def _parameters_filter(stress_type):
            """Set parameters according stress_type"""
            _control_files = {'unixbench': "unixbench5.control",
                              'stress': "stress.control"}
            _check_cmds = {'unixbench': "pidof -s ./Run",
                           'stress': "pidof -s stress"}
            _stop_cmds = {'unixbench': "killall ./Run",
                          'stress': "killall stress"}
            try:
                control_file = _control_files[stress_type]
                self.control_path = os.path.join(data_dir.get_root_dir(),
                                                 "shared/control",
                                                 control_file)
                self.check_cmd = _check_cmds[stress_type]
                self.stop_cmd = _stop_cmds[stress_type]
            except KeyError:
                self.control_path = ""
                self.check_cmd = ""
                self.stop_cmd = ""

        self.params = {}
        if params:
            self.params = params
        self.timeout = 60
        self.stress_type = stress_type
        self.host_stress_process = None
        if stress_type not in ["stress", "unixbench"]:
            raise StressError("Stress %s is not supported now." % stress_type)

        _parameters_filter(stress_type)
        self.stress_args = self.params.get("stress_args", "")

    @error.context_aware
    def load_stress_tool(self):
        """
        load stress tool on host.
        """
        # Run stress tool on host.
        from autotest.client import common
        autotest_client_dir = os.path.dirname(common.__file__)
        autotest_local_path = os.path.join(autotest_client_dir,
                                           "autotest-local")
        args = [autotest_local_path, '--args=%s' % self.stress_args,
                self.control_path, '--verbose']
        self.host_stress_process = subprocess.Popen(args)

        running = utils_misc.wait_for(self.app_running, first=0.5, timeout=60)
        if not running:
            raise StressError("Stress tool %s isn't running"
                              % self.stress_type)

    @error.context_aware
    def unload_stress(self):
        """
        stop stress tool manually
        """
        def _unload_stress():
            if self.host_stress_process is not None:
                utils_misc.kill_process_tree(self.host_stress_process.pid)
            if not self.app_running():
                return True
            return False

        error.context("stop stress app on host", logging.info)
        utils_misc.wait_for(_unload_stress, first=2.0,
                            text="wait stress app quit", step=1.0, timeout=60)

    def app_running(self):
        """
        check whether app really run in background
        """
        result = utils.run(self.check_cmd, timeout=60, ignore_status=True)
        return result.exit_status == 0


def load_stress(stress_type, vms, params):
    """
    Load stress for tests.

    :param stress_type: The stress type you need
    :param params: Useful parameters for stress
    :param vms: Used when it's stress in vms
    """
    fail_info = []
    # Add stress tool in vms
    if stress_type == "stress_in_vms":
        for vm in vms:
            try:
                vstress = VMStress(vm, "stress")
                vstress.load_stress_tool()
            except StressError, detail:
                fail_info.append("Launch stress in %s failed:%s" % (vm.name,
                                                                    detail))
    # Add stress for host
    elif stress_type == "stress_on_host":
        try:
            hstress = HostStress(params, "stress")
            hstress.load_stress_tool()
        except StressError, detail:
            fail_info.append("Launch stress on host failed:%s" % str(detail))
    # Booting vm for following test
    elif stress_type == "load_vm_booting":
        load_vms = params.get("load_vms", [])
        if len(load_vms):
            load_vm = load_vms[0]
            try:
                if load_vm.is_alive():
                    load_vm.destroy()
                load_vm.start()
            except virt_vm.VMStartError:
                fail_info.append("Start load vm %s failed." % load_vm.name)
        else:
            fail_info.append("No load vm provided.")
    # Booting vms for following test
    elif stress_type == "load_vms_booting":
        load_vms = params.get("load_vms", [])
        for load_vm in load_vms:
            if load_vm.is_alive():
                load_vm.destroy()
        # Booting load_vms at same time
        for load_vm in load_vms:
            try:
                load_vm.start()
            except virt_vm.VMStartError:
                fail_info.append("Start load vm %s failed." % load_vm.name)
                break
    # Booting test vms for following test
    elif stress_type == "vms_booting":
        for vm in vms:
            if vm.is_alive():
                vm.destroy()
        try:
            for vm in vms:
                vm.start()
        except virt_vm.VMStartError:
            fail_info.append("Start vms failed.")
    return fail_info


def unload_stress(stress_type, vms):
    """
    Unload stress loaded by load_stress(...).
    """
    if stress_type == "stress_in_vms":
        for vm in vms:
            VMStress(vm, "stress").unload_stress()
    elif stress_type == "stress_on_host":
        HostStress(None, "stress").unload_stress()


class RemoteDiskManager(object):

    """Control images on remote host"""

    def __init__(self, params):
        remote_host = params.get("remote_ip")
        remote_user = params.get("remote_user")
        remote_pwd = params.get("remote_pwd")
        self.runner = remote.RemoteRunner(host=remote_host,
                                          username=remote_user,
                                          password=remote_pwd)

    def get_free_space(self, disk_type, path='/', vgname=None):
        """
        Get free space of remote host for path.
        """
        if disk_type == "file":
            directory = os.path.dirname(path)
            try:
                output = self.runner.run("df %s" % directory).stdout
                logging.debug(output)
            except error.CmdError, detail:
                raise error.TestError("Get %s space failed:%s" % (directory,
                                                                  detail))
            for line in output.splitlines()[1:]:
                g_size = int(line.split()[3]) / 1048576
                return g_size
            raise error.TestError("Get %s space failed." % directory)
        elif disk_type == "lvm":
            output = self.runner.run("vgs --units=g | grep %s" % vgname).stdout
            if re.search(vgname, output.stdout):
                try:
                    return int(output.split('g')[0])
                except (IndexError, ValueError), detail:
                    output = detail
            raise error.TestError("Get VG %s space failed:%s" % (vgname,
                                                                 output))

    def occupy_space(self, disk_type, need_size, path=None, vgname=None,
                     timeout=60):
        """
        Create an image or volume to occupy the space of destination path
        """
        free = self.get_free_space(disk_type, path, vgname)
        logging.debug("Allowed space on remote path:%sGB", free)
        occupied_size = free - need_size / 2
        occupied_path = os.path.join(os.path.dirname(path), "occupied")
        return self.create_image(disk_type, occupied_path, occupied_size,
                                 vgname, "occupied", False, timeout)

    def iscsi_login_setup(self, host, target_name, is_login=True):
        """
        Login or logout to a target on remote host.
        """
        if is_login:
            discovery_cmd = "iscsiadm -m discovery -t sendtargets -p %s" % host
            output = self.runner.run(discovery_cmd, ignore_status=True).stdout
            if target_name not in output:
                raise error.TestError("Discovery %s on %s failed."
                                      % (target_name, host))
            cmd = "iscsiadm --mode node --login --targetname %s" % target_name
            output = self.runner.run(cmd).stdout
            if "successful" not in output:
                raise error.TestError("Login to %s failed." % target_name)
            else:
                cmd = "iscsiadm -m session -P 3"
                output = self.runner.run(cmd).stdout
                pattern = r"Target:\s+%s.*?disk\s(\w+)\s+\S+\srunning" % target_name
                device_name = re.findall(pattern, output, re.S)
                try:
                    return "/dev/%s" % device_name[0]
                except IndexError:
                    raise error.TestError("Can not find target '%s' after login."
                                          % self.target)
        else:
            if target_name:
                cmd = "iscsiadm --mode node --logout -T %s" % target_name
            else:
                cmd = "iscsiadm --mode node --logout all"
            output = self.runner.run(cmd, ignore_status=True).stdout
            if "successful" not in output:
                logging.error("Logout to %s failed.", target_name)

    def create_vg(self, vgname, device):
        """
        Create volume group with provided device.
        """
        try:
            self.runner.run("vgs | grep %s" % vgname)
            logging.debug("Volume group %s does already exist.", vgname)
            return True
        except error.CmdError:
            pass    # Not found
        try:
            self.runner.run("vgcreate %s %s" % (vgname, device))
            return True
        except error.CmdError, detail:
            logging.error("Create vgroup '%s' on remote host failed:%s",
                          vgname, detail)
            return False

    def remove_vg(self, vgname):
        """
        Remove volume group on remote host.
        """
        try:
            self.runner.run("vgremove -f %s" % vgname)
        except error.CmdError:
            return False
        return True

    def create_image(self, disk_type, path=None, size=10, vgname=None,
                     lvname=None, sparse=True, timeout=60):
        """
        Create an image for target path.
        """
        if disk_type == "file":
            self.runner.run("mkdir -p %s" % os.path.dirname(path))
            if not os.path.basename(path):
                path = os.path.join(path, "temp.img")
            if sparse:
                cmd = "qemu-img create %s %sG" % (path, size)
            else:
                cmd = "dd if=/dev/zero of=%s bs=1G count=%s" % (path, size)
        elif disk_type == "lvm":
            if sparse:
                cmd = "lvcreate -V %sG %s --name %s --size 1M" % (size, vgname,
                                                                  lvname)
            else:
                cmd = "lvcreate -L %sG %s --name %s" % (size, vgname, lvname)
            path = "/dev/%s/%s" % (vgname, lvname)

        result = self.runner.run(cmd, ignore_status=True, timeout=timeout)
        logging.debug(result)
        if result.exit_status:
            raise error.TestFail("Create image '%s' on remote host failed."
                                 % path)
        else:
            return path

    def remove_path(self, disk_type, path):
        """
        Only allowed to remove path to file or volume.
        """
        if disk_type == "file":
            if os.path.isdir(path):
                return
            self.runner.run("rm -f %s" % path, ignore_status=True)
        elif disk_type == "lvm":
            self.runner.run("lvremove -f %s" % path, ignore_status=True)


def check_dest_vm_network(vm, ip, remote_host, username, password):
    """
    Ping migrated vms on remote host.
    """
    runner = remote.RemoteRunner(host=remote_host, username=username,
                                 password=password)
    # Timeout to wait vm's network
    logging.debug("Verifying VM IP...")
    timeout = 60
    ping_failed = True
    ping_cmd = "ping -c 4 %s" % ip
    while timeout > 0:
        ping_result = runner.run(ping_cmd, ignore_status=True)
        if ping_result.exit_status:
            time.sleep(5)
            timeout -= 5
            continue
        ping_failed = False
        break
    if ping_failed:
        raise error.TestFail("Check %s IP failed:%s" % (vm.name,
                                                        ping_result.stdout))


def canonicalize_disk_address(disk_address):
    """
    Canonicalize disk address.
    Convert {decimal|octal|hexadecimal} to decimal
    pci:0x0000.0x00.0x0b.0x0 => pci:0.0.11.0
    ide:00.00.00 => ide:0.0.0
    scsi:00.00.0x11 => scsi:0.0.17
    """
    add_info = disk_address.split(":")
    add_bus_type = add_info[0]
    add_detail = add_info[-1]
    add_detail_str = ""
    for add_item in add_detail.split("."):
        add_detail_str += ("%s." % int(add_item, 0))
    add_detail_str = "%s:%s" % (add_bus_type, add_detail_str[:-1])

    return add_detail_str
