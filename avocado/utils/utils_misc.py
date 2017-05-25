"""
Virtualization test utility functions.

:copyright: 2008-2009 Red Hat Inc.
"""

import time
import os
import re
import logging
import shutil
import platform
import threading

from aexpect.utils.genio import _open_log_files
from . import process
from . import aurl

import data_dir

ARCH = platform.machine()
_log_file_dir = data_dir.get_tmp_dir()
_log_lock = threading.RLock()


def _acquire_lock(lock, timeout=10):
    end_time = time.time() + timeout
    while time.time() < end_time:
        if lock.acquire(False):
            return True
        time.sleep(0.05)
    return False


class LogLockError(Exception):
    """
    Exception for Log Lock Error.
    """
    pass


def log_line(filename, line):
    """
    Write a line to a file.

    :param filename: Path of file to write to, either absolute or relative to
                     the dir set by set_log_file_dir().
    :param line: Line to write.
    """
    global _open_log_files, _log_file_dir, _log_lock

    if not _acquire_lock(_log_lock):
        raise LogLockError("Could not acquire exclusive lock to access"
                           " _open_log_files")
    log_file = get_log_filename(filename)
    base_file = os.path.basename(log_file)
    try:
        if base_file not in _open_log_files:
            # First, let's close the log files opened in old directories
            close_log_file(base_file)
            # Then, let's open the new file
            try:
                os.makedirs(os.path.dirname(log_file))
            except OSError:
                pass
            _open_log_files[base_file] = open(log_file, "w")
        timestr = time.strftime("%Y-%m-%d %H:%M:%S")
        _open_log_files[base_file].write("%s: %s\n" % (timestr, line))
        _open_log_files[base_file].flush()
    finally:
        _log_lock.release()


def get_log_filename(filename):
    """return full path of log file name"""
    return get_path(_log_file_dir, filename)


def close_log_file(filename):
    """close log file"""
    global _open_log_files, _log_file_dir, _log_lock
    remove = []
    if not _acquire_lock(_log_lock):
        raise LogLockError("Could not acquire exclusive lock to access"
                           " _open_log_files")
    try:
        for k in _open_log_files:
            if os.path.basename(k) == filename:
                file_pointer = _open_log_files[k]
                file_pointer.close()
                remove.append(k)
        if remove:
            for key_to_remove in remove:
                _open_log_files.pop(key_to_remove)
    finally:
        _log_lock.release()

# The following are miscellaneous utility functions.


def get_path(base_path, user_path):
    """
    Translate a user specified path to a real path.
    If user_path is relative, append it to base_path.
    If user_path is absolute, return it as is.

    :param base_path: The base path of relative user specified paths.
    :param user_path: The user specified path.
    """
    if aurl.is_url(user_path):
        return user_path
    if not os.path.isabs(user_path):
        user_path = os.path.join(base_path, user_path)
        user_path = os.path.abspath(user_path)
    return os.path.realpath(user_path)


def safe_rmdir(path, timeout=10):
    """
    Try to remove a directory safely, even on NFS filesystems.

    Sometimes, when running an autotest client test on an NFS filesystem, when
    not all filedescriptors are closed, NFS will create some temporary files,
    that will make shutil.rmtree to fail with error 39 (directory not empty).
    So let's keep trying for a reasonable amount of time before giving up.

    :param path: Path to a directory to be removed.
    :type path: string
    :param timeout: Time that the function will try to remove the dir before
                    giving up (seconds)
    :type timeout: int
    :raises: OSError, with errno 39 in case after the timeout
             shutil.rmtree could not successfuly complete. If any attempt
             to rmtree fails with errno different than 39, that exception
             will be just raised.
    """
    assert os.path.isdir(path), "Invalid directory to remove %s" % path
    step = int(timeout / 10)
    start_time = time.time()
    success = False
    attempts = 0
    while int(time.time() - start_time) < timeout:
        attempts += 1
        try:
            shutil.rmtree(path)
            success = True
            break
        except OSError, err_info:
            # We are only going to try if the error happened due to
            # directory not empty (errno 39). Otherwise, raise the
            # original exception.
            if err_info.errno != 39:
                raise
            time.sleep(step)

    if not success:
        raise OSError(39,
                      "Could not delete directory %s "
                      "after %d s and %d attempts." %
                      (path, timeout, attempts))


def umount(src, mount_point, fstype, verbose=False, fstype_mtab=None):
    """
    Umount the src mounted in mount_point.

    :src: mount source
    :mount_point: mount point
    :type: file system type
    :param fstype_mtab: file system type in mtab could be different
    :type fstype_mtab: str
    """
    if fstype_mtab is None:
        fstype_mtab = fstype

    if is_mounted(src, mount_point, fstype, None, verbose, fstype_mtab):
        umount_cmd = "umount %s" % mount_point
        try:
            process.system(umount_cmd, verbose=verbose)
            return True
        except process.CmdError:
            return False
    else:
        logging.debug("%s is not mounted under %s", src, mount_point)
        return True


def mount(src, mount_point, fstype, perm=None, verbose=False,
          fstype_mtab=None):
    """
    Mount the src into mount_point of the host.

    :src: mount source
    :mount_point: mount point
    :fstype: file system type
    :perm: mount permission
    :param fstype_mtab: file system type in mtab could be different
    :type fstype_mtab: str
    """
    if perm is None:
        perm = "rw"
    if fstype_mtab is None:
        fstype_mtab = fstype

    if is_mounted(src, mount_point, fstype, perm, verbose, fstype_mtab):
        logging.debug("%s is already mounted in %s with %s",
                      src, mount_point, perm)
        return True
    mount_cmd = "mount -t %s %s %s -o %s" % (fstype, src, mount_point, perm)
    try:
        process.system(mount_cmd, verbose=verbose)
    except process.CmdError:
        return False
    return is_mounted(src, mount_point, fstype, perm, verbose, fstype_mtab)


def is_mounted(src, mount_point, fstype, perm=None, verbose=False,
               fstype_mtab=None):
    """
    Check mount status from /etc/mtab

    :param src: mount source
    :type src: string
    :param mount_point: mount point
    :type mount_point: string
    :param fstype: file system type
    :type fstype: string
    :param perm: mount permission
    :type perm: string
    :param verbose: if display mtab content
    :type verbose: Boolean
    :param fstype_mtab: file system type in mtab could be different
    :type fstype_mtab: str
    :return: if the src is mounted as expect
    :rtype: Boolean
    """
    if perm is None:
        perm = ""
    if fstype_mtab is None:
        fstype_mtab = fstype

    # Version 4 nfs displays 'nfs4' in mtab
    if fstype == "nfs":
        fstype_mtab = r"nfs\d?"

    mount_point = os.path.realpath(mount_point)
    if fstype not in ['nfs', 'smbfs', 'glusterfs', 'hugetlbfs']:
        if src:
            src = os.path.realpath(src)
        else:
            # Allow no passed src(None or "")
            src = ""
    mount_string = "%s %s .*%s %s" % (src, mount_point, fstype_mtab, perm)
    logging.debug("Searching '%s' in mtab...", mount_string)
    if verbose:
        logging.debug("/etc/mtab contents:\n%s", file("/etc/mtab").read())
    if re.findall(mount_string.strip(), file("/etc/mtab").read()):
        logging.debug("%s is mounted.", src)
        return True
    else:
        logging.debug("%s is not mounted.", src)
        return False
