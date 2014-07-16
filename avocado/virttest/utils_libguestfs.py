"""
libguestfs tools test utility functions.
"""

import logging
import signal
import os
import re

from autotest.client import os_dep, utils
from autotest.client.shared import error
import aexpect
import propcan


class LibguestfsCmdError(Exception):

    """
    Error of libguestfs-tool command.
    """

    def __init__(self, details=''):
        self.details = details
        Exception.__init__(self)

    def __str__(self):
        return str(self.details)


def lgf_cmd_check(cmd):
    """
    To check whether the cmd is supported on this host.

    :param cmd: the cmd to use a libguest tool.
    :return: None if the cmd is not exist, otherwise return its path.
    """
    libguestfs_cmds = ['libguestfs-test-tool', 'guestfish', 'guestmount',
                       'virt-alignment-scan', 'virt-cat', 'virt-copy-in',
                       'virt-copy-out', 'virt-df', 'virt-edit',
                       'virt-filesystems', 'virt-format', 'virt-inspector',
                       'virt-list-filesystems', 'virt-list-partitions',
                       'virt-ls', 'virt-make-fs', 'virt-rescue',
                       'virt-resize', 'virt-sparsify', 'virt-sysprep',
                       'virt-tar', 'virt-tar-in', 'virt-tar-out',
                       'virt-win-reg', 'virt-inspector2']

    if cmd not in libguestfs_cmds:
        raise LibguestfsCmdError(
            "Command %s is not supported by libguestfs yet." % cmd)

    try:
        return os_dep.command(cmd)
    except ValueError:
        logging.warning("You have not installed %s on this host.", cmd)
        return None


def lgf_command(cmd, ignore_status=True, debug=False, timeout=60):
    """
    Interface of libguestfs tools' commands.

    :param cmd: Command line to execute.
    :return: CmdResult object.
    :raise: LibguestfsCmdError if non-zero exit status
            and ignore_status=False
    """
    if debug:
        logging.debug("Running command %s in debug mode.", cmd)

    # Raise exception if ignore_status is False
    try:
        ret = utils.run(cmd, ignore_status=ignore_status,
                        verbose=debug, timeout=timeout)
    except error.CmdError, detail:
        raise LibguestfsCmdError(detail)

    if debug:
        logging.debug("status: %s", ret.exit_status)
        logging.debug("stdout: %s", ret.stdout.strip())
        logging.debug("stderr: %s", ret.stderr.strip())

    # Return CmdResult instance when ignore_status is True
    return ret


class LibguestfsBase(propcan.PropCanBase):

    """
    Base class of libguestfs tools.
    """

    __slots__ = ['ignore_status', 'debug', 'timeout', 'uri', 'lgf_exec']

    def __init__(self, lgf_exec="/bin/true", ignore_status=True,
                 debug=False, timeout=60, uri=None):
        init_dict = {}
        init_dict['ignore_status'] = ignore_status
        init_dict['debug'] = debug
        init_dict['timeout'] = timeout
        init_dict['uri'] = uri
        init_dict['lgf_exec'] = lgf_exec
        super(LibguestfsBase, self).__init__(init_dict)

    def set_ignore_status(self, ignore_status):
        """
        Enforce setting ignore_status as a boolean.
        """
        if bool(ignore_status):
            self.__dict_set__('ignore_status', True)
        else:
            self.__dict_set__('ignore_status', False)

    def set_debug(self, debug):
        """
        Accessor method for 'debug' property that logs message on change
        """
        if not self.INITIALIZED:
            self.__dict_set__('debug', debug)
        else:
            current_setting = self.__dict_get__('debug')
            desired_setting = bool(debug)
            if not current_setting and desired_setting:
                self.__dict_set__('debug', True)
                logging.debug("Libguestfs debugging enabled")
            # current and desired could both be True
            if current_setting and not desired_setting:
                self.__dict_set__('debug', False)
                logging.debug("Libguestfs debugging disabled")

    def set_timeout(self, timeout):
        """
        Accessor method for 'timeout' property, timeout should be digit
        """
        if type(timeout) is int:
            self.__dict_set__('timeout', timeout)
        else:
            try:
                timeout = int(str(timeout))
                self.__dict_set__('timeout', timeout)
            except ValueError:
                logging.debug("Set timeout failed.")

    def get_uri(self):
        """
        Accessor method for 'uri' property that must exist
        """
        # self.get() would call get_uri() recursivly
        try:
            return self.__dict_get__('uri')
        except KeyError:
            return None


# There are two ways to call guestfish:
# 1.Guestfish classies provided below(shell session)
# 2.guestfs module provided in system libguestfs package

class Guestfish(LibguestfsBase):

    """
    Execute guestfish, using a new guestfish shell each time.
    """

    __slots__ = []

    def __init__(self, disk_img=None, ro_mode=False,
                 libvirt_domain=None, inspector=False,
                 uri=None, mount_options=None, run_mode="interactive"):
        """
        Initialize guestfish command with options.

        :param disk_img: if it is not None, use option '-a disk'.
        :param ro_mode: only for disk_img. add option '--ro' if it is True.
        :param libvirt_domain: if it is not None, use option '-d domain'.
        :param inspector: guestfish mounts vm's disks automatically
        :param uri: guestfish's connect uri
        :param mount_options: Mount the named partition or logical volume
                               on the given mountpoint.
        """
        guestfs_exec = "guestfish"
        if lgf_cmd_check(guestfs_exec) is None:
            raise LibguestfsCmdError

        if run_mode not in ['remote', 'interactive']:
            raise AssertionError("run_mode should be remote or interactive")

        if run_mode == "remote":
            guestfs_exec += " --listen"
        else:
            if uri:
                guestfs_exec += " -c '%s'" % uri
            if disk_img:
                guestfs_exec += " -a '%s'" % disk_img
            if libvirt_domain:
                guestfs_exec += " -d '%s'" % libvirt_domain
            if ro_mode:
                guestfs_exec += " --ro"
            if inspector:
                guestfs_exec += " -i"
            if mount_options is not None:
                guestfs_exec += " --mount %s" % mount_options

        super(Guestfish, self).__init__(guestfs_exec)

    def complete_cmd(self, command):
        """
        Execute built-in command in a complete guestfish command
        (Not a guestfish session).
        command: guestfish [--options] [commands]
        """
        guestfs_exec = self.__dict_get__('lgf_exec')
        ignore_status = self.__dict_get__('ignore_status')
        debug = self.__dict_get__('debug')
        timeout = self.__dict_get__('timeout')
        if command:
            guestfs_exec += " %s" % command
            return lgf_command(guestfs_exec, ignore_status, debug, timeout)
        else:
            raise LibguestfsCmdError("No built-in command was passed.")


class GuestfishSession(aexpect.ShellSession):

    """
    A shell session of guestfish.
    """

    # Check output against list of known error-status strings
    ERROR_REGEX_LIST = ['libguestfs: error:\s*']

    def __init__(self, guestfs_exec=None, a_id=None, prompt=r"><fs>\s*"):
        """
        Initialize guestfish session server, or client if id set.

        :param guestfs_cmd: path to guestfish executable
        :param id: ID of an already running server, if accessing a running
                server, or None if starting a new one.
        :param prompt: Regular expression describing the shell's prompt line.
        """
        # aexpect tries to auto close session because no clients connected yet
        super(GuestfishSession, self).__init__(guestfs_exec, a_id,
                                               prompt=prompt,
                                               auto_close=False)

    def cmd_status_output(self, cmd, timeout=60, internal_timeout=None,
                          print_func=None):
        """
        Send a guestfish command and return its exit status and output.

        :param cmd: guestfish command to send
                    (must not contain newline characters)
        :param timeout: The duration (in seconds) to wait for the prompt to
                return
        :param internal_timeout: The timeout to pass to read_nonblocking
        :param print_func: A function to be used to print the data being read
                (should take a string parameter)
        :return: A tuple (status, output) where status is the exit status and
                output is the output of cmd
        :raise ShellTimeoutError: Raised if timeout expires
        :raise ShellProcessTerminatedError: Raised if the shell process
                terminates while waiting for output
        :raise ShellStatusError: Raised if the exit status cannot be obtained
        :raise ShellError: Raised if an unknown error occurs
        """
        out = self.cmd_output(cmd, timeout, internal_timeout, print_func)
        for line in out.splitlines():
            if self.match_patterns(line, self.ERROR_REGEX_LIST) is not None:
                return 1, out
        return 0, out

    def cmd_result(self, cmd, ignore_status=False):
        """Mimic utils.run()"""
        exit_status, stdout = self.cmd_status_output(cmd)
        stderr = ''  # no way to retrieve this separately
        result = utils.CmdResult(cmd, stdout, stderr, exit_status)
        if not ignore_status and exit_status:
            raise error.CmdError(cmd, result,
                                 "Guestfish Command returned non-zero exit status")
        return result


class GuestfishRemote(object):

    """
    Remote control of guestfish.
    """

    # Check output against list of known error-status strings
    ERROR_REGEX_LIST = ['libguestfs: error:\s*']

    def __init__(self, guestfs_exec=None, a_id=None):
        """
        Initialize guestfish session server, or client if id set.

        :param guestfs_cmd: path to guestfish executable
        :param a_id: guestfish remote id
        """
        if a_id is None:
            try:
                ret = utils.run(guestfs_exec, ignore_status=False,
                                verbose=True, timeout=60)
            except error.CmdError, detail:
                raise LibguestfsCmdError(detail)
            self.a_id = re.search("\d+", ret.stdout.strip()).group()
        else:
            self.a_id = a_id

    def get_id(self):
        return self.a_id

    def cmd_status_output(self, cmd, ignore_status=None, verbose=None, timeout=60):
        """
        Send a guestfish command and return its exit status and output.

        :param cmd: guestfish command to send(must not contain newline characters)
        :param timeout: The duration (in seconds) to wait for the prompt to return
        :return: A tuple (status, output) where status is the exit status
                 and output is the output of cmd
        :raise LibguestfsCmdError: Raised if commands execute failed
        """
        guestfs_exec = "guestfish --remote=%s " % self.a_id
        cmd = guestfs_exec + cmd
        try:
            ret = utils.run(cmd, ignore_status=ignore_status,
                            verbose=verbose, timeout=timeout)
        except error.CmdError, detail:
            raise LibguestfsCmdError(detail)

        for line in self.ERROR_REGEX_LIST:
            if re.search(line, ret.stdout.strip()):
                raise LibguestfsCmdError(detail)

        logging.debug("command: %s", cmd)
        logging.debug("stdout: %s", ret.stdout.strip())

        return 0, ret.stdout.strip()

    def cmd(self, cmd, ignore_status=False):
        """Mimic utils.run()"""
        exit_status, stdout = self.cmd_status_output(cmd)
        stderr = ''  # no way to retrieve this separately
        result = utils.CmdResult(cmd, stdout, stderr, exit_status)
        if not ignore_status and exit_status:
            raise error.CmdError(cmd, result,
                                 "Guestfish Command returned non-zero exit status")
        return result

    def cmd_result(self, cmd, ignore_status=False):
        """Mimic utils.run()"""
        exit_status, stdout = self.cmd_status_output(cmd)
        stderr = ''  # no way to retrieve this separately
        result = utils.CmdResult(cmd, stdout, stderr, exit_status)
        if not ignore_status and exit_status:
            raise error.CmdError(cmd, result,
                                 "Guestfish Command returned non-zero exit status")
        return result


class GuestfishPersistent(Guestfish):

    """
    Execute operations using persistent guestfish session.
    """

    __slots__ = ['session_id', 'run_mode']

    # Help detect leftover sessions
    SESSION_COUNTER = 0

    def __init__(self, disk_img=None, ro_mode=False,
                 libvirt_domain=None, inspector=False,
                 uri=None, mount_options=None, run_mode="interactive"):
        super(GuestfishPersistent, self).__init__(disk_img, ro_mode,
                                                  libvirt_domain, inspector,
                                                  uri, mount_options, run_mode)
        self.__dict_set__('run_mode', run_mode)

        if self.get('session_id') is None:
            # set_uri does not call when INITIALIZED = False
            # and no session_id passed to super __init__
            self.new_session()

        # Check whether guestfish session is prepared.
        guestfs_session = self.open_session()
        if run_mode != "remote":
            status, output = guestfs_session.cmd_status_output('is-config', timeout=60)
            if status != 0:
                logging.debug("Persistent guestfish session is not responding.")
                raise aexpect.ShellStatusError(self.lgf_exec, 'is-config')

    def close_session(self):
        """
        If a persistent session exists, close it down.
        """
        try:
            run_mode = self.get('run_mode')
            existing = self.open_session()
            # except clause exits function
            # Try to end session with inner command 'quit'
            try:
                existing.cmd("quit")
            # It should jump to exception followed normally
            except aexpect.ShellProcessTerminatedError:
                self.__class__.SESSION_COUNTER -= 1
                self.__dict_del__('session_id')
                return  # guestfish session was closed normally
            # Close with 'quit' did not respond
            # So close with aexpect functions
            if run_mode != "remote":
                if existing.is_alive():
                    # try nicely first
                    existing.close()
                    if existing.is_alive():
                        # Be mean, incase it's hung
                        existing.close(sig=signal.SIGTERM)
                    # Keep count:
                    self.__class__.SESSION_COUNTER -= 1
                    self.__dict_del__('session_id')
        except LibguestfsCmdError:
            # Allow other exceptions to be raised
            pass  # session was closed already

    def new_session(self):
        """
        Open new session, closing any existing
        """
        # Accessors may call this method, avoid recursion
        # Must exist, can't be None
        guestfs_exec = self.__dict_get__('lgf_exec')
        self.close_session()
        # Always create new session
        run_mode = self.get('run_mode')
        if run_mode == "remote":
            new_session = GuestfishRemote(guestfs_exec)
        else:
            new_session = GuestfishSession(guestfs_exec)
        # Keep count
        self.__class__.SESSION_COUNTER += 1
        session_id = new_session.get_id()
        self.__dict_set__('session_id', session_id)

    def open_session(self):
        """
        Return session with session_id in this class.
        """
        try:
            session_id = self.__dict_get__('session_id')
            run_mode = self.get('run_mode')
            if session_id:
                try:
                    if run_mode == "remote":
                        return GuestfishRemote(a_id=session_id)
                    else:
                        return GuestfishSession(a_id=session_id)
                except aexpect.ShellStatusError:
                    # session was already closed
                    self.__dict_del__('session_id')
                    raise LibguestfsCmdError(
                        "Open session '%s' failed." % session_id)
        except KeyError:
            raise LibguestfsCmdError("No session id.")

    # Inner command for guestfish should be executed in a guestfish session
    def inner_cmd(self, command):
        """
        Execute inner command of guestfish in a pesistent session.

        :param command: inner command to be executed.
        """
        session = self.open_session()
        # Allow to raise error by default.
        ignore_status = self.__dict_get__('ignore_status')
        return session.cmd_result(command, ignore_status=ignore_status)

    def add_drive(self, filename):
        """
        add-drive - add an image to examine or modify

        This function is the equivalent of calling "add_drive_opts" with no
        optional parameters, so the disk is added writable, with the format
        being detected automatically.
        """
        return self.inner_cmd("add-drive %s" % filename)

    def add_drive_opts(self, filename, readonly=False, format=None,
                       iface=None, name=None):
        """
        add-drive-opts - add an image to examine or modify.

        This function adds a disk image called "filename" to the handle.
        "filename" may be a regular host file or a host device.
        """
        cmd = "add-drive-opts %s" % filename

        if readonly:
            cmd += " readonly:true"
        else:
            cmd += " readonly:false"
        if format:
            cmd += " format:%s" % format
        if iface:
            cmd += " iface:%s" % iface
        if name:
            cmd += " name:%s" % name

        return self.inner_cmd(cmd)

    def add_drive_ro(self, filename):
        """
        add-ro/add-drive-ro - add a drive in snapshot mode (read-only)

        This function is the equivalent of calling "add_drive_opts" with the
        optional parameter "GUESTFS_ADD_DRIVE_OPTS_READONLY" set to 1, so the
        disk is added read-only, with the format being detected automatically.
        """
        return self.inner_cmd("add-drive-ro %s" % filename)

    def add_domain(self, domain, libvirturi=None, readonly=False, iface=None,
                   live=False, allowuuid=False, readonlydisk=None):
        """
        domain/add-domain - add the disk(s) from a named libvirt domain

        This function adds the disk(s) attached to the named libvirt domain
        "dom". It works by connecting to libvirt, requesting the domain and
        domain XML from libvirt, parsing it for disks, and calling
        "add_drive_opts" on each one.
        """
        cmd = "add-domain %s" % domain

        if libvirturi:
            cmd += " libvirturi:%s" % libvirturi
        if readonly:
            cmd += " readonly:true"
        else:
            cmd += " readonly:false"
        if iface:
            cmd += " iface:%s" % iface
        if live:
            cmd += " live:true"
        if allowuuid:
            cmd += " allowuuid:true"
        if readonlydisk:
            cmd += " readonlydisk:%s" % readonlydisk

        return self.inner_cmd(cmd)

    def run(self):
        """
        run/launch - launch the qemu subprocess

        Internally libguestfs is implemented by running a virtual machine
        using qemu.
        """
        return self.inner_cmd("launch")

    def df(self):
        """
        df - report file system disk space usage

        This command runs the "df" command to report disk space used.
        """
        return self.inner_cmd("df")

    def list_partitions(self):
        """
        list-partitions - list the partitions

        List all the partitions detected on all block devices.
        """
        return self.inner_cmd("list-partitions")

    def mount(self, device, mountpoint):
        """
        mount - mount a guest disk at a position in the filesystem

        Mount a guest disk at a position in the filesystem.
        """
        return self.inner_cmd("mount %s %s" % (device, mountpoint))

    def mount_ro(self, device, mountpoint):
        """
        mount-ro - mount a guest disk, read-only

        This is the same as the "mount" command, but it mounts the
        filesystem with the read-only (*-o ro*) flag.
        """
        return self.inner_cmd("mount-ro %s %s" % (device, mountpoint))

    def mount_options(self, options, device, mountpoint):
        """
        mount - mount a guest disk at a position in the filesystem

        Mount a guest disk at a position in the filesystem.
        """
        return self.inner_cmd("mount-options %s %s %s" % (options, device, mountpoint))

    def mounts(self):
        """
        mounts - show mounted filesystems

        This returns the list of currently mounted filesystems.
        """
        return self.inner_cmd("mounts")

    def mountpoints(self):
        """
        mountpoints - show mountpoints

        This call is similar to "mounts".
        That call returns a list of devices.
        """
        return self.inner_cmd("mountpoints")

    def do_mount(self, mountpoint):
        """
        do_mount - Automaticly mount

        Mount a lvm or physical partation to '/'
        """
        partition_type = self.params.get("partition_type")
        if partition_type == "lvm":
            vg_name = self.params.get("vg_name", "vol_test")
            lv_name = self.params.get("lv_name", "vol_file")
            device = "/dev/%s/%s" % (vg_name, lv_name)
            logging.info("mount lvm partition...%s" % device)
        elif partition_type == "physical":
            pv_name = self.params.get("pv_name", "/dev/sdb")
            device = pv_name + "1"
            logging.info("mount physical partition...%s" % device)
        self.mount(device, mountpoint)

    def read_file(self, path):
        """
        read-file - read a file

        This calls returns the contents of the file "path" as a buffer.
        """
        return self.inner_cmd("read-file %s" % path)

    def cat(self, path):
        """
        cat - list the contents of a file

        Return the contents of the file named "path".
        """
        return self.inner_cmd("cat %s" % path)

    def write(self, path, content):
        """
        write - create a new file

        This call creates a file called "path". The content of the file
        is the string "content" (which can contain any 8 bit data).
        """
        return self.inner_cmd("write '%s' '%s'" % (path, content))

    def write_append(self, path, content):
        """
        write-append - append content to end of file

        This call appends "content" to the end of file "path".
        If "path" does not exist, then a new file is created.
        """
        return self.inner_cmd("write-append '%s' '%s'" % (path, content))

    def inspect_os(self):
        """
        inspect-os - inspect disk and return list of operating systems found

        This function uses other libguestfs functions and certain heuristics to
        inspect the disk(s) (usually disks belonging to a virtual machine),
        looking for operating systems.
        """
        return self.inner_cmd("inspect-os")

    def inspect_get_roots(self):
        """
        inspect-get-roots - return list of operating systems found by
        last inspection

        This function is a convenient way to get the list of root devices
        """
        return self.inner_cmd("inspect-get-roots")

    def inspect_get_arch(self, root):
        """
        inspect-get-arch - get architecture of inspected operating system

        This returns the architecture of the inspected operating system.
        """
        return self.inner_cmd("inspect-get-arch %s" % root)

    def inspect_get_distro(self, root):
        """
        inspect-get-distro - get distro of inspected operating system

        This returns the distro (distribution) of the inspected
        operating system.
        """
        return self.inner_cmd("inspect-get-distro %s" % root)

    def inspect_get_filesystems(self, root):
        """
        inspect-get-filesystems - get filesystems associated with inspected
        operating system

        This returns a list of all the filesystems that we think are associated
        with this operating system.
        """
        return self.inner_cmd("inspect-get-filesystems %s" % root)

    def inspect_get_hostname(self, root):
        """
        inspect-get-hostname - get hostname of the operating system

        This function returns the hostname of the operating system as found by
        inspection of the guest's configuration files.
        """
        return self.inner_cmd("inspect-get-hostname %s" % root)

    def inspect_get_major_version(self, root):
        """
        inspect-get-major-version - get major version of inspected operating
        system

        This returns the major version number of the inspected
        operating system.
        """
        return self.inner_cmd("inspect-get-major-version %s" % root)

    def inspect_get_minor_version(self, root):
        """
        inspect-get-minor-version - get minor version of inspected operating
        system

        This returns the minor version number of the inspected operating system
        """
        return self.inner_cmd("inspect-get-minor-version %s" % root)

    def inspect_get_mountpoints(self, root):
        """
        inspect-get-mountpoints - get mountpoints of inspected operating system

        This returns a hash of where we think the filesystems associated with
        this operating system should be mounted.
        """
        return self.inner_cmd("inspect-get-mountpoints %s" % root)

    def list_filesystems(self):
        """
        list-filesystems - list filesystems

        This inspection command looks for filesystems on partitions, block
        devices and logical volumes, returning a list of devices containing
        filesystems and their type.
        """
        return self.inner_cmd("list-filesystems")

    def list_devices(self):
        """
        list-devices - list the block devices

        List all the block devices.
        """
        return self.inner_cmd("list-devices")

    def tar_out(self, directory, tarfile):
        """
        tar-out - pack directory into tarfile

        This command packs the contents of "directory" and downloads it
        to local file "tarfile".
        """
        return self.inner_cmd("tar-out %s %s" % (directory, tarfile))

    def tar_in(self, tarfile, directory):
        """
        tar-in - unpack tarfile to directory

        This command uploads and unpacks local file "tarfile"
        (an *uncompressed* tar file) into "directory".
        """
        return self.inner_cmd("tar-in %s %s" % (tarfile, directory))

    def tar_in_opts(self, tarfile, directory, compress=None):
        """
        tar-in-opts - unpack tarfile to directory

        This command uploads and unpacks local file "tarfile"
        (an *compressed* tar file) into "directory".
        """
        if compress:
            return self.inner_cmd("tar-in-opts %s %s compress:%s" % (tarfile, directory, compress))
        else:
            return self.inner_cmd("tar-in-opts %s %s" % (tarfile, directory))

    def file_architecture(self, filename):
        """
        file-architecture - detect the architecture of a binary file

        This detects the architecture of the binary "filename", and returns it
        if known.
        """
        return self.inner_cmd("file-architecture %s" % filename)

    def filesize(self, file):
        """
        filesize - return the size of the file in bytes

        This command returns the size of "file" in bytes.
        """
        return self.inner_cmd("filesize %s" % file)

    def stat(self, path):
        """
        stat - get file information

        Returns file information for the given "path".
        """
        return self.inner_cmd("stat %s" % path)

    def lstat(self, path):
        """
        lstat - get file information for a symbolic link

        Returns file information for the given "path".
        """
        return self.inner_cmd("lstat %s" % path)

    def lstatlist(self, path, names):
        """
        lstatlist - lstat on multiple files

        This call allows you to perform the "lstat" operation on multiple files,
        where all files are in the directory "path". "names" is the list of
        files from this directory.
        """
        return self.inner_cmd("lstatlist %s %s" % (path, names))

    def umask(self, mask):
        """
        umask - set file mode creation mask (umask)

        This function sets the mask used for creating new files and device nodes
        to "mask & 0777".
        """
        return self.inner_cmd("umask %s" % mask)

    def get_umask(self):
        """
        get-umask - get the current umask

        Return the current umask. By default the umask is 022 unless it has been
        set by calling "umask".
        """
        return self.inner_cmd("get-umask")

    def mkdir(self, path):
        """
        mkdir - create a directory

        Create a directory named "path".
        """
        return self.inner_cmd("mkdir %s" % path)

    def mkdir_mode(self, path, mode):
        """
        mkdir-mode - create a directory with a particular mode

        This command creates a directory, setting the initial permissions of the
        directory to "mode".
        """
        return self.inner_cmd("mkdir-mode %s %s" % (path, mode))

    def mknod(self, mode, devmajor, devminor, path):
        """
        mknod - make block, character or FIFO devices

        This call creates block or character special devices, or named pipes
        (FIFOs).
        """
        return self.inner_cmd("mknod %s %s %s %s" % (mode, devmajor, devminor, path))

    def rm_rf(self, path):
        """
        rm-rf - remove a file or directory recursively

        Remove the file or directory "path", recursively removing the contents
        if its a directory. This is like the "rm -rf" shell command.
        """
        return self.inner_cmd("rm-rf %s" % path)

    def copy_out(self, remote, localdir):
        """
        copy-out - copy remote files or directories out of an image

        "copy-out" copies remote files or directories recursively out of the
        disk image, placing them on the host disk in a local directory called
        "localdir" (which must exist).
        """
        return self.inner_cmd("copy-out %s %s" % (remote, localdir))

    def copy_in(self, local, remotedir):
        """
        copy-in - copy local files or directories into an image

        "copy-in" copies local files or directories recursively into the disk
        image, placing them in the directory called "/remotedir" (which must
        exist).
        """
        return self.inner_cmd("copy-in %s /%s" % (local, remotedir))

    def chmod(self, mode, path):
        """
        chmod - change file mode

        Change the mode (permissions) of "path" to "mode". Only numeric modes
        are supported.
        """
        return self.inner_cmd("chmod %s %s" % (mode, path))

    def chown(self, owner, group, path):
        """
        chown - change file owner and group

        Change the file owner to "owner" and group to "group".
        """
        return self.inner_cmd("chown %s %s %s" % (owner, group, path))

    def lchown(self, owner, group, path):
        """
        lchown - change file owner and group

        Change the file owner to "owner" and group to "group". This is like
        "chown" but if "path" is a symlink then the link itself is changed, not
        the target.
        """
        return self.inner_cmd("lchown %s %s %s" % (owner, group, path))

    def du(self, path):
        """
        du - estimate file space usage

        This command runs the "du -s" command to estimate file space usage for
        "path".
        """
        return self.inner_cmd("du %s" % path)

    def file(self, path):
        """
        file - determine file type

        This call uses the standard file(1) command to determine the type or
        contents of the file.
        """
        return self.inner_cmd("file %s" % path)

    def rm(self, path):
        """
        rm - remove a file

        Remove the single file "path".
        """
        return self.inner_cmd("rm %s" % path)

    def is_file(self, path, followsymlinks=None):
        """
        is-file - test if a regular file

        This returns "true" if and only if there is a regular file with the
        given "path" name.
        """
        cmd = "is-file %s" % path

        if followsymlinks:
            cmd += " followsymlinks:%s" % followsymlinks

        return self.inner_cmd(cmd)

    def is_file_opts(self, path, followsymlinks=None):
        """
        is-file_opts - test if a regular file

        This returns "true" if and only if there is a regular file with the
        given "path" name.

        An alias of command is-file
        """
        cmd = "is-file-opts %s" % path

        if followsymlinks:
            cmd += " followsymlinks:%s" % followsymlinks

        return self.inner_cmd(cmd)

    def is_blockdev(self, path, followsymlinks=None):
        """
        is-blockdev - test if block device

        This returns "true" if and only if there is a block device with the
        given "path" name
        """
        cmd = "is-blockdev %s" % path

        if followsymlinks:
            cmd += " followsymlinks:%s" % followsymlinks

        return self.inner_cmd(cmd)

    def is_blockdev_opts(self, path, followsymlinks=None):
        """
        is-blockdev_opts - test if block device

        This returns "true" if and only if there is a block device with the
        given "path" name

        An alias of command is-blockdev
        """
        cmd = "is-blockdev-opts %s" % path

        if followsymlinks:
            cmd += " followsymlinks:%s" % followsymlinks

        return self.inner_cmd(cmd)

    def is_chardev(self, path, followsymlinks=None):
        """
        is-chardev - test if character device

        This returns "true" if and only if there is a character device with the
        given "path" name.
        """
        cmd = "is-chardev %s" % path

        if followsymlinks:
            cmd += " followsymlinks:%s" % followsymlinks

        return self.inner_cmd(cmd)

    def is_chardev_opts(self, path, followsymlinks=None):
        """
        is-chardev_opts - test if character device

        This returns "true" if and only if there is a character device with the
        given "path" name.

        An alias of command is-chardev
        """
        cmd = "is-chardev-opts %s" % path

        if followsymlinks:
            cmd += " followsymlinks:%s" % followsymlinks

        return self.inner_cmd(cmd)

    def is_dir(self, path, followsymlinks=None):
        """
        is-dir - test if a directory

        This returns "true" if and only if there is a directory with the given
        "path" name. Note that it returns false for other objects like files.
        """
        cmd = "is-dir %s" % path

        if followsymlinks:
            cmd += " followsymlinks:%s" % followsymlinks

        return self.inner_cmd(cmd)

    def is_dir_opts(self, path, followsymlinks=None):
        """
        is-dir-opts - test if character device

        This returns "true" if and only if there is a character device with the
        given "path" name.

        An alias of command is-dir
        """
        cmd = "is-dir-opts %s" % path

        if followsymlinks:
            cmd += " followsymlinks:%s" % followsymlinks

        return self.inner_cmd(cmd)

    def is_fifo(self, path, followsymlinks=None):
        """
        is-fifo - test if FIFO (named pipe)

        This returns "true" if and only if there is a FIFO (named pipe) with
        the given "path" name.
        """
        cmd = "is-fifo %s" % path

        if followsymlinks:
            cmd += " followsymlinks:%s" % followsymlinks

        return self.inner_cmd(cmd)

    def is_fifo_opts(self, path, followsymlinks=None):
        """
        is-fifo-opts - test if FIFO (named pipe)

        This returns "true" if and only if there is a FIFO (named pipe) with
        the given "path" name.

        An alias of command is-fifo
        """
        cmd = "is-fifo-opts %s" % path

        if followsymlinks:
            cmd += " followsymlinks:%s" % followsymlinks

        return self.inner_cmd(cmd)

    def is_lv(self, device):
        """
        is-lv - test if device is a logical volume

        This command tests whether "device" is a logical volume, and returns
        true iff this is the case.
        """
        return self.inner_cmd("is-lv %s" % device)

    def is_socket(self, path, followsymlinks=None):
        """
        is-socket - test if socket

        This returns "true" if and only if there is a Unix domain socket with
        the given "path" name.
        """
        cmd = "is-socket %s" % path

        if followsymlinks:
            cmd += " followsymlinks:%s" % followsymlinks

        return self.inner_cmd(cmd)

    def is_socket_opts(self, path, followsymlinks=None):
        """
        is-socket-opts - test if socket

        This returns "true" if and only if there is a Unix domain socket with
        the given "path" name.

        An alias of command is-socket
        """
        cmd = "is-socket-opts %s" % path

        if followsymlinks:
            cmd += " followsymlinks:%s" % followsymlinks

        return self.inner_cmd(cmd)

    def is_symlink(self, path):
        """
        is-symlink - test if symbolic link

        This returns "true" if and only if there is a symbolic link with the
        given "path" name.
        """
        return self.inner_cmd("is-symlink %s" % path)

    def is_whole_device(self, device):
        """
        is-symlink - test if symbolic link

        This returns "true" if and only if "device" refers to a whole block
        device. That is, not a partition or a logical device.
        """
        return self.inner_cmd("is-whole-device %s" % device)

    def is_zero(self, path):
        """
        is-zero - test if a file contains all zero bytes

        This returns true iff the file exists and the file is empty or it
        contains all zero bytes.
        """
        return self.inner_cmd("is-zero %s" % path)

    def is_zero_device(self, device):
        """
        is-zero-device - test if a device contains all zero bytes

        This returns true iff the device exists and contains all zero bytes.
        Note that for large devices this can take a long time to run.
        """
        return self.inner_cmd("is-zero-device %s" % device)

    def cp(self, src, dest):
        """
        cp - copy a file

        This copies a file from "src" to "dest" where "dest" is either a
        destination filename or destination directory.
        """
        return self.inner_cmd("cp %s %s" % (src, dest))

    def exists(self, path):
        """
        exists - test if file or directory exists

        This returns "true" if and only if there is a file, directory (or
        anything) with the given "path" name
        """
        return self.inner_cmd("exists %s" % path)

    def cp_a(self, src, dest):
        """
        cp-a - copy a file or directory recursively

        This copies a file or directory from "src" to "dest" recursively using
        the "cp -a" command.
        """
        return self.inner_cmd("cp-a %s %s" % (src, dest))

    def equal(self, file1, file2):
        """
        equal - test if two files have equal contents

        This compares the two files "file1" and "file2" and returns true if
        their content is exactly equal, or false otherwise.
        """
        return self.inner_cmd("equal %s %s" % (file1, file2))

    def fill(self, c, len, path):
        """
        fill - fill a file with octets

        This command creates a new file called "path". The initial content of
        the file is "len" octets of "c", where "c" must be a number in the range
        "[0..255]".
        """
        return self.inner_cmd("fill %s %s %s" % (c, len, path))

    def fill_dir(self, dir, nr):
        """
        fill-dir - fill a directory with empty files

        This function, useful for testing filesystems, creates "nr" empty files
        in the directory "dir" with names 00000000 through "nr-1" (ie. each file
        name is 8 digits long padded with zeroes).
        """
        return self.inner_cmd("fill-dir %s %s" % (dir, nr))

    def fill_pattern(self, pattern, len, path):
        """
        fill-pattern - fill a file with a repeating pattern of bytes

        This function is like "fill" except that it creates a new file of length
        "len" containing the repeating pattern of bytes in "pattern". The
        pattern is truncated if necessary to ensure the length of the file is
        exactly "len" bytes.
        """
        return self.inner_cmd("fill-pattern %s %s %s" % (pattern, len, path))

    def strings(self, path):
        """
        strings - print the printable strings in a file

        This runs the strings(1) command on a file and returns the list of
        printable strings found.
        """
        return self.inner_cmd("strings %s" % path)

    def head(self, path):
        """
        head - return first 10 lines of a file

        This command returns up to the first 10 lines of a file as a list of
        strings.
        """
        return self.inner_cmd("head %s" % path)

    def head_n(self, nrlines, path):
        """
        head-n - return first N lines of a file

        If the parameter "nrlines" is a positive number, this returns the first
        "nrlines" lines of the file "path".
        """
        return self.inner_cmd("head-n %s %s" % (nrlines, path))

    def tail(self, path):
        """
        tail - return last 10 lines of a file

        This command returns up to the last 10 lines of a file as a list of
        strings.
        """
        return self.inner_cmd("tail %s" % path)

    def pread(self, path, count, offset):
        """
        pread - read part of a file

        This command lets you read part of a file. It reads "count" bytes of the
        file, starting at "offset", from file "path".
        """
        return self.inner_cmd("pread %s %s %s" % (path, count, offset))

    def hexdump(self, path):
        """
        hexdump - dump a file in hexadecimal

        This runs "hexdump -C" on the given "path". The result is the
        human-readable, canonical hex dump of the file.
        """
        return self.inner_cmd("hexdump %s" % path)

    def more(self, filename):
        """
        more - view a file

        This is used to view a file.
        """
        return self.inner_cmd("more %s" % filename)

    def download(self, remotefilename, filename):
        """
        download - download a file to the local machine

        Download file "remotefilename" and save it as "filename" on the local
        machine.
        """
        return self.inner_cmd("download %s %s" % (remotefilename, filename))

    def part_init(self, device, parttype):
        """
        part-init - create an empty partition table

        This creates an empty partition table on "device" of one of the
        partition types listed below. Usually "parttype" should be either
        "msdos" or "gpt" (for large disks).
        """
        return self.inner_cmd("part-init %s %s" % (device, parttype))

    def part_add(self, device, prlogex, startsect, endsect):
        """
        part-add - add a partition to the device

        This command adds a partition to "device". If there is no partition
        table on the device, call "part_init" first.
        """
        cmd = "part-add %s %s %s %s" % (device, prlogex, startsect, endsect)
        return self.inner_cmd(cmd)

    def part_del(self, device, partnum):
        """
        part-del device partnum

        This command deletes the partition numbered "partnum" on "device".

        Note that in the case of MBR partitioning, deleting an extended
        partition also deletes any logical partitions it contains.
        """
        return self.inner_cmd("part_del %s %s" % (device, partnum))

    def part_set_bootable(self, device, partnum, bootable):
        """
        part-set-bootable device partnum bootable

        This sets the bootable flag on partition numbered "partnum" on device
        "device". Note that partitions are numbered from 1.
        """
        return self.inner_cmd("part-set-bootable %s %s %s" % (device, partnum, bootable))

    def part_set_mbr_id(self, device, partnum, idbyte):
        """
        part-set-mbr-id - set the MBR type byte (ID byte) of a partition

        Sets the MBR type byte (also known as the ID byte) of the numbered
        partition "partnum" to "idbyte". Note that the type bytes quoted in
        most documentation are in fact hexadecimal numbers, but usually documented
        without any leading "0x" which might be confusing.
        """
        return self.inner_cmd("part-set-mbr-id %s %s %s" % (device, partnum, idbyte))

    def part_set_name(self, device, partnum, name):
        """
        part-set-name - set partition name

        This sets the partition name on partition numbered "partnum" on device
        "device". Note that partitions are numbered from 1.
        """
        return self.inner_cmd("part-set-name %s %s %s" % (device, partnum, name))

    def part_to_dev(self, partition):
        """
        part-to-dev - convert partition name to device name

        This function takes a partition name (eg. "/dev/sdb1") and removes the
        partition number, returning the device name (eg. "/dev/sdb").

        The named partition must exist, for example as a string returned from
        "list_partitions".
        """
        return self.inner_cmd("part-to-dev %s" % partition)

    def part_to_partnum(self, partition):
        """
        part-to-partnum - convert partition name to partition number

        This function takes a partition name (eg. "/dev/sdb1") and returns the
        partition number (eg. 1).

        The named partition must exist, for example as a string returned from
        "list_partitions".
        """
        return self.inner_cmd("part_to_partnum %s" % partition)

    def checksum(self, csumtype, path):
        """
        checksum - compute MD5, SHAx or CRC checksum of file

        This call computes the MD5, SHAx or CRC checksum of the file named
        "path".
        """
        return self.inner_cmd("checksum %s %s" % (csumtype, path))

    def checksum_device(self, csumtype, device):
        """
        checksum-device - compute MD5, SHAx or CRC checksum of the contents of a
        device

        This call computes the MD5, SHAx or CRC checksum of the contents of the
        device named "device". For the types of checksums supported see the
        "checksum" command.
        """
        return self.inner_cmd("checksum-device %s %s" % (csumtype, device))

    def checksums_out(self, csumtype, directory, sumsfile):
        """
        checksums-out - compute MD5, SHAx or CRC checksum of files in a
        directory

        This command computes the checksums of all regular files in "directory"
        and then emits a list of those checksums to the local output file
        "sumsfile".
        """
        return self.inner_cmd("checksums-out %s %s %s" % (csumtype, directory, sumsfile))

    def is_config(self):
        """
        is-config - is ready to accept commands

        This returns true if this handle is in the "CONFIG" state
        """
        return self.inner_cmd("is-config")

    def is_ready(self):
        """
        is-ready - is ready to accept commands

        This returns true if this handle is ready to accept commands
        (in the "READY" state).
        """
        return self.inner_cmd("is-ready")

    def part_list(self, device):
        """
        part-list - list partitions on a device

        This command parses the partition table on "device" and
        returns the list of partitions found.
        """
        return self.inner_cmd("part-list %s" % device)

    def mkfs(self, fstype, device):
        """
        mkfs - make a filesystem

        This creates a filesystem on "device" (usually a partition or LVM
        logical volume). The filesystem type is "fstype", for example "ext3".
        """
        return self.inner_cmd("mkfs %s %s" % (fstype, device))

    def mkfs_opts(self, fstype, device, opts):
        """
        mkfs-opts - make a filesystem with optional arguments

        This creates a filesystem on "device" (usually a partition or LVM
        logical volume). The filesystem type is "fstype", for example "ext3".
        """
        return self.inner_cmd("mkfs %s %s %s" % (fstype, device, opts))

    def part_disk(self, device, parttype):
        """
        part-disk - partition whole disk with a single primary partition

        This command is simply a combination of "part_init" followed by
        "part_add" to create a single primary partition covering
        the whole disk.
        """
        return self.inner_cmd("part-disk %s %s" % (device, parttype))

    def part_get_bootable(self, device, partnum):
        """
        part-get-bootable - return true if a partition is bootable

        This command returns true if the partition "partnum" on "device"
        has the bootable flag set.
        """
        return self.inner_cmd("part-get-bootable %s %s" % (device, partnum))

    def part_get_mbr_id(self, device, partnum):
        """
        part-get-mbr-id - get the MBR type byte (ID byte) from a partition

        Returns the MBR type byte (also known as the ID byte) from the
        numbered partition "partnum".
        """
        return self.inner_cmd("part-get-mbr-id %s %s" % (device, partnum))

    def part_get_parttype(self, device):
        """
        part-get-parttype - get the partition table type

        This command examines the partition table on "device" and returns the
        partition table type (format) being used.
        """
        return self.inner_cmd("part-get-parttype %s" % device)

    def fsck(self, fstype, device):
        """
        fsck - run the filesystem checker

        This runs the filesystem checker (fsck) on "device" which should have
        filesystem type "fstype".
        """
        return self.inner_cmd("fsck %s %s" % (fstype, device))

    def blockdev_getss(self, device):
        """
        blockdev-getss - get sectorsize of block device

        This returns the size of sectors on a block device. Usually 512,
        but can be larger for modern devices.
        """
        return self.inner_cmd("blockdev-getss %s" % device)

    def blockdev_getsz(self, device):
        """
        blockdev-getsz - get total size of device in 512-byte sectors

        This returns the size of the device in units of 512-byte sectors
        (even if the sectorsize isn't 512 bytes ... weird).
        """
        return self.inner_cmd("blockdev-getsz %s" % device)

    def blockdev_getbsz(self, device):
        """
        blockdev-getbsz - get blocksize of block device

        This returns the block size of a device.
        """
        return self.inner_cmd("blockdev-getbsz %s" % device)

    def blockdev_getsize64(self, device):
        """
        blockdev-getsize64 - get total size of device in bytes

        This returns the size of the device in bytes
        """
        return self.inner_cmd("blockdev-getsize64 %s" % device)

    def blockdev_setbsz(self, device, blocksize):
        """
        blockdev-setbsz - set blocksize of block device

        This sets the block size of a device.
        """
        return self.inner_cmd("blockdev-setbsz %s %s" % (device, blocksize))

    def blockdev_getro(self, device):
        """
        blockdev-getro - is block device set to read-only

        Returns a boolean indicating if the block device is read-only
        (true if read-only, false if not).
        """
        return self.inner_cmd("blockdev-getro %s" % device)

    def blockdev_setro(self, device):
        """
        blockdev-setro - set block device to read-only

        Sets the block device named "device" to read-only.
        """
        return self.inner_cmd("blockdev-setro %s" % device)

    def blockdev_setrw(self, device):
        """
        blockdev-setrw - set block device to read-write

        Sets the block device named "device" to read-write.
        """
        return self.inner_cmd("blockdev-setrw %s" % device)

    def blockdev_flushbufs(self, device):
        """
        blockdev-flushbufs - flush device buffers

        This tells the kernel to flush internal buffers associated with
        "device".
        """
        return self.inner_cmd("blockdev-flushbufs %s" % device)

    def blockdev_rereadpt(self, device):
        """
        blockdev-rereadpt - reread partition table

        Reread the partition table on "device".
        """
        return self.inner_cmd("blockdev-rereadpt %s" % device)

    def canonical_device_name(self, device):
        """
        canonical-device-name - return canonical device name

        This utility function is useful when displaying device names to
        the user.
        """
        return self.inner_cmd("canonical-device-name %s" % device)

    def device_index(self, device):
        """
        device-index - convert device to index

        This function takes a device name (eg. "/dev/sdb") and returns the
        index of the device in the list of devices
        """
        return self.inner_cmd("device-index %s" % device)

    def disk_format(self, filename):
        """
        disk-format - detect the disk format of a disk image

        Detect and return the format of the disk image called "filename",
        "filename" can also be a host device, etc
        """
        return self.inner_cmd("disk-format %s" % filename)

    def disk_has_backing_file(self, filename):
        """
        disk-has-backing-file - return whether disk has a backing file

        Detect and return whether the disk image "filename" has a backing file
        """
        return self.inner_cmd("disk-has-backing-file %s" % filename)

    def disk_virtual_size(self, filename):
        """
        disk-virtual-size - return virtual size of a disk

        Detect and return the virtual size in bytes of the disk image"
        """
        return self.inner_cmd("disk-virtual-size %s" % filename)

    def max_disks(self):
        """
        max-disks - maximum number of disks that may be added

        Return the maximum number of disks that may be added to a handle
        """
        return self.inner_cmd("max-disks")

    def nr_devices(self):
        """
        nr-devices - return number of whole block devices (disks) added

        This returns the number of whole block devices that were added
        """
        return self.inner_cmd("nr-devices")

    def scrub_device(self, device):
        """
        scrub-device - scrub (securely wipe) a device

        This command writes patterns over "device" to make data retrieval more
        difficult
        """
        return self.inner_cmd("scrub-device %s" % device)

    def scrub_file(self, file):
        """
        scrub-file - scrub (securely wipe) a file

        This command writes patterns over a file to make data retrieval more
        difficult
        """
        return self.inner_cmd("scrub-file %s" % file)

    def scrub_freespace(self, dir):
        """
        scrub-freespace - scrub (securely wipe) free space

        This command creates the directory "dir" and then fills it with files
        until the filesystem is full,and scrubs the files as for "scrub_file",
        and deletes them. The intention is to scrub any free space on the
        partition containing "dir"
        """
        return self.inner_cmd("scrub-freespace %s" % dir)

    def md_create(self, name, device, missingbitmap=None, nrdevices=None,
                  spare=None, chunk=None, level=None):
        """
        md-create - create a Linux md (RAID) device

        Create a Linux md (RAID) device named "name" on the devices in the list
        "devices".
        """
        cmd = "md-create %s %s" % (name, device)

        if missingbitmap:
            cmd += " missingbitmap:%s" % missingbitmap
        if nrdevices:
            cmd += " nrdevices:%s" % nrdevices
        if spare:
            cmd += " spare:%s" % spare
        if chunk:
            cmd += " chunk:%s" % chunk
        if level:
            cmd += " level:%s" % level

        return self.inner_cmd(cmd)

    def list_md_devices(self):
        """
        list-md-devices - list Linux md (RAID) devices

        List all Linux md devices.
        """
        return self.inner_cmd("list-md-devices")

    def md_stop(self, md):
        """
        md-stop - stop a Linux md (RAID) device

        This command deactivates the MD array named "md".
        The device is stopped, but it is not destroyed or zeroed.
        """
        return self.inner_cmd("md-stop %s" % md)

    def md_stat(self, md):
        """
        md-stat - get underlying devices from an MD device

        This call returns a list of the underlying devices which make up the
        single software RAID array device "md".
        """
        return self.inner_cmd("md-stat %s" % md)

    def md_detail(self, md):
        """
        md-detail - obtain metadata for an MD device

        This command exposes the output of 'mdadm -DY <md>'. The following
        fields are usually present in the returned hash. Other fields may also
        be present.
        """
        return self.inner_cmd("md-detail %s" % md)

    def sfdisk(self, device, cyls, heads, sectors, lines):
        """
        sfdisk - create partitions on a block device

        This is a direct interface to the sfdisk(8) program for creating
        partitions on block devices.

        *This function is deprecated.* In new code, use the "part-add" call
        instead.

        Deprecated functions will not be removed from the API, but the fact
        that they are deprecated indicates that there are problems with correct
        use of these functions.
        """
        return self.inner_cmd("sfdisk %s %s %s %s %s"
                              % (device, cyls, heads, sectors, lines))

    def sfdisk_l(self, device):
        """
        sfdisk-l - display the partition table

        This displays the partition table on "device", in the human-readable
        output of the sfdisk(8) command. It is not intended to be parsed.

        *This function is deprecated.* In new code, use the "part-list" call
        instead.
        """
        return self.inner_cmd("sfdisk-l %s" % device)

    def sfdiskM(self, device, lines):
        """
        sfdiskM - create partitions on a block device

        This is a simplified interface to the "sfdisk" command, where partition
        sizes are specified in megabytes only (rounded to the nearest cylinder)
        and you don't need to specify the cyls, heads and sectors parameters
        which were rarely if ever used anyway.

        *This function is deprecated.* In new code, use the "part-add" call
        instead.
        """
        return self.inner_cmd("sfdiskM %s %s" % (device, lines))

    def sfdisk_N(self, device, partnum, cyls, heads, sectors, line):
        """
        sfdisk-N - modify a single partition on a block device

        This runs sfdisk(8) option to modify just the single partition "n"
        (note: "n" counts from 1).

        For other parameters, see "sfdisk". You should usually pass 0 for the
        cyls/heads/sectors parameters.

        *This function is deprecated.* In new code, use the "part-add" call
        instead.
        """
        return self.inner_cmd("sfdisk-N %s %s %s %s %s %s"
                              % (device, partnum, cyls, heads, sectors, line))

    def sfdisk_disk_geometry(self, device):
        """
        sfdisk-disk-geometry - display the disk geometry from the partition
        table

        This displays the disk geometry of "device" read from the partition
        table. Especially in the case where the underlying block device has
        been resized, this can be different from the kernel's idea of the
        geometry
        """
        return self.inner_cmd("sfdisk-disk-geometry %s" % device)

    def sfdisk_kernel_geometry(self, device):
        """
        sfdisk-kernel-geometry - display the kernel geometry

        This displays the kernel's idea of the geometry of "device".
        """
        return self.inner_cmd("sfdisk-kernel-geometry %s" % device)

    def pvcreate(self, physvols):
        """
        pvcreate - create an LVM physical volume

        This creates an LVM physical volume called "physvols".
        """
        return self.inner_cmd("pvcreate %s" % (physvols))

    def pvs(self):
        """
        pvs - list the LVM physical volumes (PVs)

        List all the physical volumes detected. This is the equivalent of the
        pvs(8) command.
        """
        return self.inner_cmd("pvs")

    def pvs_full(self):
        """
        pvs-full - list the LVM physical volumes (PVs)

        List all the physical volumes detected. This is the equivalent of the
        pvs(8) command. The "full" version includes all fields.
        """
        return self.inner_cmd("pvs-full")

    def pvresize(self, device):
        """
        pvresize - resize an LVM physical volume

        This resizes (expands or shrinks) an existing LVM physical volume to
        match the new size of the underlying device
        """
        return self.inner_cmd("pvresize %s" % device)

    def pvresize_size(self, device, size):
        """
        pvresize-size - resize an LVM physical volume (with size)

        This command is the same as "pvresize" except that it allows you to
        specify the new size (in bytes) explicitly.
        """
        return self.inner_cmd("pvresize-size %s %s" % (device, size))

    def pvremove(self, device):
        """
        pvremove - remove an LVM physical volume

        This wipes a physical volume "device" so that LVM will no longer
        recognise it.

        The implementation uses the "pvremove" command which refuses to wipe
        physical volumes that contain any volume groups, so you have to remove
        those first.
        """
        return self.inner_cmd("pvremove %s" % device)

    def pvuuid(self, device):
        """
        pvuuid - get the UUID of a physical volume

        This command returns the UUID of the LVM PV "device".
        """
        return self.inner_cmd("pvuuid %s" % device)

    def vgcreate(self, volgroup, physvols):
        """
        vgcreate - create an LVM volume group

        This creates an LVM volume group called "volgroup" from the
        non-empty list of physical volumes "physvols".
        """
        return self.inner_cmd("vgcreate %s %s" % (volgroup, physvols))

    def vgs(self):
        """
        vgs - list the LVM volume groups (VGs)

        List all the volumes groups detected.
        """
        return self.inner_cmd("vgs")

    def vgs_full(self):
        """
        vgs-full - list the LVM volume groups (VGs)

        List all the volumes groups detected. This is the equivalent of the
        vgs(8) command. The "full" version includes all fields.
        """
        return self.inner_cmd("vgs-full")

    def vgrename(self, volgroup, newvolgroup):
        """
        vgrename - rename an LVM volume group

        Rename a volume group "volgroup" with the new name "newvolgroup".
        """
        return self.inner_cmd("vgrename %s %s" % (volgroup, newvolgroup))

    def vgremove(self, vgname):
        """
        vgremove - remove an LVM volume group

        Remove an LVM volume group "vgname", (for example "VG").
        """
        return self.inner_cmd("vgremove %s" % vgname)

    def vgscan(self):
        """
        vgscan - rescan for LVM physical volumes, volume groups and logical
        volumes

        This rescans all block devices and rebuilds the list of LVM physical
        volumes, volume groups and logical volumes.
        """
        return self.inner_cmd("vgscan")

    def vguuid(self, vgname):
        """
        vguuid - get the UUID of a volume group

        This command returns the UUID of the LVM VG named "vgname"
        """
        return self.inner_cmd("vguuid %s" % vgname)

    def vg_activate(self, activate, volgroups):
        """
        vg-activate - activate or deactivate some volume groups

        This command activates or (if "activate" is false) deactivates all
        logical volumes in the listed volume groups "volgroups"
        """
        return self.inner_cmd("vg-activate %s %s" % (activate, volgroups))

    def vg_activate_all(self, activate):
        """
        vg-activate-all - activate or deactivate all volume groups

        This command activates or (if "activate" is false) deactivates all
        logical volumes in all volume groups.
        """
        return self.inner_cmd("vg-activate-all %s" % activate)

    def vglvuuids(self, vgname):
        """
        vglvuuids - get the LV UUIDs of all LVs in the volume group

        Given a VG called "vgname", this returns the UUIDs of all the logical
        volumes created in this volume group.
        """
        return self.inner_cmd("vglvuuids %s" % vgname)

    def vgpvuuids(self, vgname):
        """
        vgpvuuids - get the PV UUIDs containing the volume group

        Given a VG called "vgname", this returns the UUIDs of all the physical
        volumes that this volume group resides on.
        """
        return self.inner_cmd("vgpvuuids %s" % vgname)

    def lvcreate(self, logvol, volgroup, mbytes):
        """
        lvcreate - create an LVM logical volume

        This creates an LVM logical volume called "logvol" on the
        volume group "volgroup", with "size" megabytes.
        """
        return self.inner_cmd("lvcreate %s %s %s" % (logvol, volgroup, mbytes))

    def lvuuid(self, device):
        """
        lvuuid - get the UUID of a logical volume

        This command returns the UUID of the LVM LV "device".
        """
        return self.inner_cmd("lvuuid %s" % device)

    def lvm_canonical_lv_name(self, lvname):
        """
        lvm-canonical-lv-name - get canonical name of an LV

        This converts alternative naming schemes for LVs that you might
        find to the canonical name.
        """
        return self.inner_cmd("lvm-canonical-lv-name %s" % lvname)

    def lvremove(self, device):
        """
        lvremove - remove an LVM logical volume

        Remove an LVM logical volume "device", where "device" is the path
        to the LV, such as "/dev/VG/LV".
        """
        return self.inner_cmd("lvremove %s" % device)

    def lvresize(self, device, mbytes):
        """
        lvresize - resize an LVM logical volume

        This resizes (expands or shrinks) an existing LVM logical volume to
        "mbytes".
        """
        return self.inner_cmd("lvresize %s %s" % (device, mbytes))

    def lvs(self):
        """
        lvs - list the LVM logical volumes (LVs)

        List all the logical volumes detected.
        """
        return self.inner_cmd("lvs")

    def lvs_full(self):
        """
        lvs-full - list the LVM logical volumes (LVs)

        List all the logical volumes detected. This is the equivalent of the
        lvs(8) command. The "full" version includes all fields.
        """
        return self.inner_cmd("lvs-full")

    def lvm_clear_filter(self):
        """
        lvm-clear-filter - clear LVM device filter

        This undoes the effect of "lvm_set_filter". LVM will be able to see
        every block device.
        This command also clears the LVM cache and performs a volume group scan.
        """
        return self.inner_cmd("lvm-clear-filter")

    def lvm_remove_all(self):
        """
        lvm-remove-all - remove all LVM LVs, VGs and PVs

        This command removes all LVM logical volumes, volume groups and physical
        volumes.
        """
        return self.inner_cmd("lvm-remove-all")

    def lvm_set_filter(self, device):
        """
        lvm-set-filter - set LVM device filter

        This sets the LVM device filter so that LVM will only be able to "see"
        the block devices in the list "devices", and will ignore all other
        attached block devices.
        """
        return self.inner_cmd("lvm-set-filter %s" % device)

    def lvresize_free(self, lv, percent):
        """
        lvresize-free - expand an LV to fill free space

        This expands an existing logical volume "lv" so that it fills "pc"% of
        the remaining free space in the volume group. Commonly you would call
        this with pc = 100 which expands the logical volume as much as possible,
        using all remaining free space in the volume group.
        """
        return self.inner_cmd("lvresize-free %s %s" % (lv, percent))

    def lvrename(self, logvol, newlogvol):
        """
        lvrename - rename an LVM logical volume

        Rename a logical volume "logvol" with the new name "newlogvol"
        """
        return self.inner_cmd("lvrename %s %s" % (logvol, newlogvol))

    def vfs_type(self, mountable):
        """
        vfs-type - get the Linux VFS type corresponding to a mounted device

        Gets the filesystem type corresponding to the filesystem on "mountable"
        """
        return self.inner_cmd("vfs-type %s" % (mountable))

    def touch(self, path):
        """
        touch - update file timestamps or create a new file

        Touch acts like the touch(1) command. It can be used to update the
        timestamps on a file, or, if the file does not exist, to create a new
        zero-length file.
        """
        return self.inner_cmd("touch %s" % (path))

    def umount_all(self):
        """
        umount-all - unmount all filesystems

        This unmounts all mounted filesystems.
        Some internal mounts are not unmounted by this call.
        """
        return self.inner_cmd("umount-all")

    def ls(self, directory):
        """
        ls - list the files in a directory

        List the files in "directory" (relative to the root directory, there is
        no cwd). The '.' and '..' entries are not returned, but hidden files are
        shown.
        """
        return self.inner_cmd("ls %s" % (directory))

    def ll(self, directory):
        """
        ll - list the files in a directory (long format)

        List the files in "directory" (relative to the root directory, there is
        no cwd) in the format of 'ls -la'.
        """
        return self.inner_cmd("ll %s" % (directory))

    def sync(self):
        """
        lsync - sync disks, writes are flushed through to the disk image

        This syncs the disk, so that any writes are flushed through to the
        underlying disk image.
        """
        return self.inner_cmd("sync")

    def debug(self, subcmd, extraargs):
        """
        debug - debugging and internals

        The "debug" command exposes some internals of "guestfsd" (the guestfs
        daemon) that runs inside the hypervisor.
        """
        return self.inner_cmd("debug %s %s" % (subcmd, extraargs))

# libguestfs module functions follow #####


def libguest_test_tool_cmd(qemuarg=None, qemudirarg=None,
                           timeoutarg=None, ignore_status=True,
                           debug=False, timeout=60):
    """
    Execute libguest-test-tool command.

    :param qemuarg: the qemu option
    :param qemudirarg: the qemudir option
    :param timeoutarg: the timeout option
    :return: a CmdResult object
    :raise: raise LibguestfsCmdError
    """
    cmd = "libguestfs-test-tool"
    if qemuarg is not None:
        cmd += " --qemu '%s'" % qemuarg
    if qemudirarg is not None:
        cmd += " --qemudir '%s'" % qemudirarg
    if timeoutarg is not None:
        cmd += " --timeout %s" % timeoutarg

    # Allow to raise LibguestfsCmdError if ignore_status is False.
    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_edit_cmd(disk_or_domain, file_path, is_disk=False, options=None,
                  extra=None, expr=None, connect_uri=None, ignore_status=True,
                  debug=False, timeout=60):
    """
    Execute virt-edit command to check whether it is ok.

    Since virt-edit will need uses' interact, maintain and return
    a session if there is no raise after command has been executed.

    :param disk_or_domain: a img path or a domain name.
    :param file_path: the file need to be edited in img file.
    :param options: the options of virt-edit.
    :param extra: additional suffix of command.
    :return: a session of executing virt-edit command.
    """
    # disk_or_domain and file_path are necessary parameters.
    cmd = "virt-edit"
    if connect_uri is not None:
        cmd += " -c %s" % connect_uri
    if is_disk:
        cmd += " -a %s" % disk_or_domain
    else:
        cmd += " -d %s" % disk_or_domain
    cmd += " %s" % file_path
    if options is not None:
        cmd += " %s" % options
    if extra is not None:
        cmd += " %s" % extra
    if expr is not None:
        cmd += " -e '%s'" % expr

    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_clone_cmd(original, newname=None, autoclone=False, **dargs):
    """
    Clone existing virtual machine images.

    :param original: Name of the original guest to be cloned.
    :param newname: Name of the new guest virtual machine instance.
    :param autoclone: Generate a new guest name, and paths for new storage.
    :param dargs: Standardized function API keywords. There are many
                  options not listed, they can be passed in dargs.
    """
    def storage_config(cmd, options):
        """Configure options for storage"""
        # files should be a list
        files = options.get("files", [])
        if len(files):
            for file in files:
                cmd += " --file '%s'" % file
        if options.get("nonsparse") is not None:
            cmd += " --nonsparse"
        return cmd

    def network_config(cmd, options):
        """Configure options for network"""
        mac = options.get("mac")
        if mac is not None:
            cmd += " --mac '%s'" % mac
        return cmd

    cmd = "virt-clone --original '%s'" % original
    if newname is not None:
        cmd += " --name '%s'" % newname
    if autoclone is True:
        cmd += " --auto-clone"
    # Many more options can be added if necessary.
    cmd = storage_config(cmd, dargs)
    cmd = network_config(cmd, dargs)

    ignore_status = dargs.get("ignore_status", True)
    debug = dargs.get("debug", False)
    timeout = dargs.get("timeout", 60)

    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_sparsify_cmd(indisk, outdisk, compress=False, convert=None,
                      format=None, ignore_status=True, debug=False,
                      timeout=60):
    """
    Make a virtual machine disk sparse.

    :param indisk: The source disk to be sparsified.
    :param outdisk: The destination disk.
    """
    cmd = "virt-sparsify"
    if compress is True:
        cmd += " --compress"
    if format is not None:
        cmd += " --format '%s'" % format
    cmd += " '%s'" % indisk

    if convert is not None:
        cmd += " --convert '%s'" % convert
    cmd += " '%s'" % outdisk
    # More options can be added if necessary.

    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_resize_cmd(indisk, outdisk, **dargs):
    """
    Resize a virtual machine disk.

    :param indisk: The source disk to be resized
    :param outdisk: The destination disk.
    """
    cmd = "virt-resize"
    ignore_status = dargs.get("ignore_status", True)
    debug = dargs.get("debug", False)
    timeout = dargs.get("timeout", 60)
    resize = dargs.get("resize")
    resized_size = dargs.get("resized_size", "0")
    expand = dargs.get("expand")
    shrink = dargs.get("shrink")
    ignore = dargs.get("ignore")
    delete = dargs.get("delete")
    if resize is not None:
        cmd += " --resize %s=%s" % (resize, resized_size)
    if expand is not None:
        cmd += " --expand %s" % expand
    if shrink is not None:
        cmd += " --shrink %s" % shrink
    if ignore is not None:
        cmd += " --ignore %s" % ignore
    if delete is not None:
        cmd += " --delete %s" % delete
    cmd += " %s %s" % (indisk, outdisk)

    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_list_partitions_cmd(disk_or_domain, long=False, total=False,
                             human_readable=False, ignore_status=True,
                             debug=False, timeout=60):
    """
    "virt-list-partitions" is a command line tool to list the partitions
    that are contained in a virtual machine or disk image.

    :param disk_or_domain: a disk or a domain to be mounted
    """
    cmd = "virt-list-partitions %s" % disk_or_domain
    if long is True:
        cmd += " --long"
    if total is True:
        cmd += " --total"
    if human_readable is True:
        cmd += " --human-readable"
    return lgf_command(cmd, ignore_status, debug, timeout)


def guestmount(disk_or_domain, mountpoint, inspector=False,
               readonly=False, **dargs):
    """
    guestmount - Mount a guest filesystem on the host using
                 FUSE and libguestfs.

    :param disk_or_domain: a disk or a domain to be mounted
           If you need to mount a disk, set is_disk to True in dargs
    :param mountpoint: the mountpoint of filesystems
    :param inspector: mount all filesystems automatically
    :param readonly: if mount filesystem with readonly option
    """
    def get_special_mountpoint(cmd, options):
        special_mountpoints = options.get("special_mountpoints", [])
        for mountpoint in special_mountpoints:
            cmd += " -m %s" % mountpoint
        return cmd

    cmd = "guestmount"
    ignore_status = dargs.get("ignore_status", True)
    debug = dargs.get("debug", False)
    timeout = dargs.get("timeout", 60)
    # If you need to mount a disk, set is_disk to True
    is_disk = dargs.get("is_disk", False)
    if is_disk is True:
        cmd += " -a %s" % disk_or_domain
    else:
        cmd += " -d %s" % disk_or_domain
    if inspector is True:
        cmd += " -i"
    if readonly is True:
        cmd += " --ro"
    cmd = get_special_mountpoint(cmd, dargs)
    cmd += " %s" % mountpoint
    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_filesystems(disk_or_domain, **dargs):
    """
    virt-filesystems - List filesystems, partitions, block devices,
    LVM in a virtual machine or disk image

    :param disk_or_domain: a disk or a domain to be mounted
           If you need to mount a disk, set is_disk to True in dargs
    """
    def get_display_type(cmd, options):
        all = options.get("all", False)
        filesystems = options.get("filesystems", False)
        extra = options.get("extra", False)
        partitions = options.get("partitions", False)
        block_devices = options.get("block_devices", False)
        logical_volumes = options.get("logical_volumes", False)
        volume_groups = options.get("volume_groups", False)
        physical_volumes = options.get("physical_volumes", False)
        long_format = options.get("long_format", False)
        human_readable = options.get("human_readable", False)
        if all is True:
            cmd += " --all"
        if filesystems is True:
            cmd += " --filesystems"
        if extra is True:
            cmd += " --extra"
        if partitions is True:
            cmd += " --partitions"
        if block_devices is True:
            cmd += " --block_devices"
        if logical_volumes is True:
            cmd += " --logical_volumes"
        if volume_groups is True:
            cmd += " --volume_groups"
        if physical_volumes is True:
            cmd += " --physical_volumes"
        if long_format is True:
            cmd += " --long"
        if human_readable is True:
            cmd += " -h"
        return cmd

    cmd = "virt-filesystems"
    # If you need to mount a disk, set is_disk to True
    is_disk = dargs.get("is_disk", False)
    ignore_status = dargs.get("ignore_status", True)
    debug = dargs.get("debug", False)
    timeout = dargs.get("timeout", 60)

    if is_disk is True:
        cmd += " -a %s" % disk_or_domain
    else:
        cmd += " -d %s" % disk_or_domain
    cmd = get_display_type(cmd, dargs)
    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_list_partitions(disk_or_domain, long=False, total=False,
                         human_readable=False, ignore_status=True,
                         debug=False, timeout=60):
    """
    "virt-list-partitions" is a command line tool to list the partitions
    that are contained in a virtual machine or disk image.

    :param disk_or_domain: a disk or a domain to be mounted
    """
    cmd = "virt-list-partitions %s" % disk_or_domain
    if long is True:
        cmd += " --long"
    if total is True:
        cmd += " --total"
    if human_readable is True:
        cmd += " --human-readable"
    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_list_filesystems(disk_or_domain, format=None, long=False,
                          all=False, ignore_status=True, debug=False,
                          timeout=60):
    """
    "virt-list-filesystems" is a command line tool to list the filesystems
    that are contained in a virtual machine or disk image.

    :param disk_or_domain: a disk or a domain to be mounted
    """
    cmd = "virt-list-filesystems %s" % disk_or_domain
    if format is not None:
        cmd += " --format %s" % format
    if long is True:
        cmd += " --long"
    if all is True:
        cmd += " --all"
    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_df(disk_or_domain, ignore_status=True, debug=False, timeout=60):
    """
    "virt-df" is a command line tool to display free space on
    virtual machine filesystems.
    """
    cmd = "virt-df %s" % disk_or_domain
    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_sysprep_cmd(disk_or_domain, options=None,
                     extra=None, ignore_status=True,
                     debug=False, timeout=600):
    """
    Execute virt-sysprep command to reset or unconfigure a virtual machine.

    :param disk_or_domain: a img path or a domain name.
    :param options: the options of virt-sysprep.
    :return: a CmdResult object.
    """
    if os.path.isfile(disk_or_domain):
        disk_or_domain = "-a " + disk_or_domain
    else:
        disk_or_domain = "-d " + disk_or_domain
    cmd = "virt-sysprep %s" % (disk_or_domain)
    if options is not None:
        cmd += " %s" % options
    if extra is not None:
        cmd += " %s" % extra

    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_cat_cmd(disk_or_domain, file_path, options=None, ignore_status=True,
                 debug=False, timeout=60):
    """
    Execute virt-cat command to print guest's file detail.

    :param disk_or_domain: a img path or a domain name.
    :param file_path: the file to print detail
    :param options: the options of virt-cat.
    :return: a CmdResult object.
    """
    # disk_or_domain and file_path are necessary parameters.
    if os.path.isfile(disk_or_domain):
        disk_or_domain = "-a " + disk_or_domain
    else:
        disk_or_domain = "-d " + disk_or_domain
    cmd = "virt-cat %s '%s'" % (disk_or_domain, file_path)
    if options is not None:
        cmd += " %s" % options

    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_tar_in(disk_or_domain, tar_file, destination, is_disk=False,
                ignore_status=True, debug=False, timeout=60):
    """
    "virt-tar-in" unpacks an uncompressed tarball into a virtual machine
    disk image or named libvirt domain.
    """
    cmd = "virt-tar-in"
    if is_disk is True:
        cmd += " -a %s" % disk_or_domain
    else:
        cmd += " -d %s" % disk_or_domain
    cmd += " %s %s" % (tar_file, destination)
    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_tar_out(disk_or_domain, directory, tar_file, is_disk=False,
                 ignore_status=True, debug=False, timeout=60):
    """
    "virt-tar-out" packs a virtual machine disk image directory into a tarball.
    """
    cmd = "virt-tar-out"
    if is_disk is True:
        cmd += " -a %s" % disk_or_domain
    else:
        cmd += " -d %s" % disk_or_domain
    cmd += " %s %s" % (directory, tar_file)
    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_copy_in(disk_or_domain, file, destination, is_disk=False,
                 ignore_status=True, debug=False, timeout=60):
    """
    "virt-copy-in" copies files and directories from the local disk into a
    virtual machine disk image or named libvirt domain.
    #TODO: expand file to files
    """
    cmd = "virt-copy-in"
    if is_disk is True:
        cmd += " -a %s" % disk_or_domain
    else:
        cmd += " -d %s" % disk_or_domain
    cmd += " %s %s" % (file, destination)
    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_copy_out(disk_or_domain, file_path, localdir, is_disk=False,
                  ignore_status=True, debug=False, timeout=60):
    """
    "virt-copy-out" copies files and directories out of a virtual machine
    disk image or named libvirt domain.
    """
    cmd = "virt-copy-out"
    if is_disk is True:
        cmd += " -a %s" % disk_or_domain
    else:
        cmd += " -d %s" % disk_or_domain
    cmd += " %s %s" % (file_path, localdir)
    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_format(disk, filesystem=None, image_format=None, lvm=None,
                partition=None, wipe=False, ignore_status=False,
                debug=False, timeout=60):
    """
    Virt-format takes an existing disk file (or it can be a host partition,
    LV etc), erases all data on it, and formats it as a blank disk.
    """
    cmd = "virt-format -a %s" % disk
    if filesystem is not None:
        cmd += " --filesystem=%s" % filesystem
    if image_format is not None:
        cmd += " --format=%s" % image_format
    if lvm is not None:
        cmd += " --lvm=%s" % lvm
    if partition is not None:
        cmd += " --partition=%s" % partition
    if wipe is True:
        cmd += " --wipe"
    return lgf_command(cmd, ignore_status, debug, timeout)


def virt_inspector(disk_or_domain, is_disk=False, ignore_status=True,
                   debug=False, timeout=30):
    """
    virt-inspector2 examines a virtual machine or disk image and tries to
    determine the version of the operating system and other information
    about the virtual machine.
    """
    # virt-inspector has been replaced by virt-inspector2 in RHEL7
    # Check it here to choose which one to be used.
    cmd = lgf_cmd_check("virt-inspector2")
    if cmd is None:
        cmd = "virt-inspector"

    # If you need to mount a disk, set is_disk to True
    if is_disk is True:
        cmd += " -a %s" % disk_or_domain
    else:
        cmd += " -d %s" % disk_or_domain
    return lgf_command(cmd, ignore_status, debug, timeout)
