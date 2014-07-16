import os
import re
from autotest.client import utils
import remote
import aexpect
import data_dir
import hashlib
import logging


class BuildError(Exception):

    def __init__(self, error_info):
        super(BuildError, self).__init__(error_info)
        self.error_info = error_info

    def __str__(self):
        e_msg = "Build Error: %s" % self.error_info
        return e_msg


class Builder(object):

    def __init__(self, params, address, source, shell_client=None,
                 shell_port=None, file_transfer_client=None,
                 file_transfer_port=None, username=None, password=None,
                 make_flags="", build_dir=None, build_dir_prefix=None,
                 shell_linesep=None, shell_prompt=None):
        """
        :param params: Dictionary with test parameters, used to get the default
                       values of all named parameters.
        :param address: Remote host or guest address
        :param source: Directory containing the source on the machine
                       where this script is running
        :param shell_client: The client to use ('ssh', 'telnet' or 'nc')
        :param shell_port: Port to connect to for the shell client
        :param file_transfer_client: The file transfer client to use ('scp' or
                                     'rss')
        :param file_transfer_port: Port to connect to for the file transfer
                                   client
        :param username: Username (if required)
        :param password: Password (if required)
        :param make_flags: Flags to pass to the make process, default: ""
        :param build_dir: Where to copy and build the files on target. If None,
                          use params['tmp_dir']
        :param build_dir_prefix: What to name the build directory on target
                                 If None, use the name of the source directory.
        :param shell_linesep: Line separator in the shell
        :param shell_prompt: Regexp that matches the prompt in the shell.
        """

        def full_build_path(build_dir, directory_prefix, make_flags):
            """
            Generates the full path for the build using the make flags and
            supplied build location.
            :return: The full path as a string
            """
            extra_flags_hash = hashlib.sha1()
            extra_flags_hash.update(make_flags)
            directory_name = "%s-%s" % (directory_prefix,
                                        (extra_flags_hash.hexdigest())[:8])
            return os.path.join(build_dir, directory_name)

        def def_helper(arg, param, default):
            if arg is None:
                return params.get(param, default)
            else:
                return arg

        self.address = address
        self.source = os.path.normpath(source)
        self.client = def_helper(shell_client, "shell_client", "ssh")
        self.port = def_helper(shell_port, "shell_port", "22")
        self.file_transfer_client = def_helper(file_transfer_client,
                                               "file_transfer_client", "scp")
        self.file_transfer_port = def_helper(file_transfer_port,
                                             "file_transfer_port", "22")
        self.username = def_helper(username, "username", "root")
        self.password = def_helper(password, "password", "redhat")
        self.make_flags = make_flags
        self.build_dir = def_helper(build_dir, "tmp_dir", "/tmp")
        if build_dir_prefix is None:
            build_dir_prefix = os.path.basename(source)
        self.full_build_path = full_build_path(self.build_dir,
                                               build_dir_prefix, make_flags)
        self.linesep = def_helper(shell_linesep, "shell_linesep", "\n")
        self.prompt = def_helper(shell_prompt, "shell_prompt",
                                 "^\[.*\][\#\$]\s*)$")

        self.session = remote.remote_login(self.client, self.address,
                                           self.port, self.username,
                                           self.password, self.prompt,
                                           self.linesep, timeout=360)

    def sync_directories(self):
        """
        Synchronize the directories between the local and remote machines
        :returns: True if any files needed to be copied; False otherwise. Does
        not support symlinks.
        """

        def get_local_hashes(path):
            """
            Create a dict of the hashes of all files in path on the local
            machine.
            :param path: Path to search
            """
            def hash_file(file_name):
                """
                Calculate hex-encoded hash of a file
                :param file_name: File to hash
                """
                f = open(file_name, mode='rb')
                h = hashlib.sha1()
                while True:
                    buf = f.read(4096)
                    if not buf:
                        break
                    h.update(buf)
                return h.hexdigest()

            def visit(arg, dir_name, file_names):
                """
                Callback function to calculate and store hashes
                :param arg: Tuple with base path and the hash that will contain
                            the results.
                :param dir_name: Current directory
                :param file_names: File names in the current directory
                """
                (base_path, result) = arg
                for file_name in file_names:
                    path = os.path.join(dir_name, file_name)
                    if os.path.isfile(path):
                        result[os.path.relpath(path, base_path)] = hash_file(path)

            result = {}
            os.path.walk(path, visit, (path, result))

            return result

        def get_remote_hashes(path, session, linesep):
            """
            Create a dict of the hashes of all files in path on the remote
            machine.
            :param path: Path to search
            :param session: Session object to use
            :param linesep: Line separation string for the remote system
            """

            cmd = 'test \! -d %s || find %s -type f | xargs sha1sum' % (path,
                                                                        path)
            status, output = session.cmd_status_output(cmd)
            if not status == 0:
                raise BuildError("Unable to get hashes of remote files: '%s'"
                                 % output)
            result = {}
            # Output is "<sum>  <filename><linesep><sum>  <filename>..."
            for line in output.split(linesep):
                if re.match("^[a-f0-9]{32,}  [^ ].*$", line):
                    (h, f) = line.split(None, 1)
                    result[os.path.relpath(f, path)] = h

            return result

        def list_recursive_dirnames(path):
            """
            List all directories that exist in path on the local machine
            :param path: Path to search
            """
            def visit(arg, dir_name, file_names):
                """
                Callback function list alla directories
                :param arg: Tuple with base path and the list that will contain
                            the results.
                :param dir_name: Current directory
                :param file_names: File names in the current directory
                """
                (base_path, result) = arg
                for file_name in file_names:
                    path = os.path.join(dir_name, file_name)
                    if os.path.isdir(path):
                        result.append(os.path.relpath(path, base_path))

            result = []
            os.path.walk(path, visit, (path, result))

            return result

        remote_hashes = get_remote_hashes(self.full_build_path, self.session,
                                          self.linesep)
        local_hashes = get_local_hashes(self.source)

        to_transfer = []
        for rel_path in local_hashes.keys():
            rhash = remote_hashes.get(rel_path)
            if rhash is None or not rhash == local_hashes[rel_path]:
                to_transfer.append(rel_path)

        need_build = False
        if to_transfer:
            logging.info("Need to copy files to %s on target" %
                         self.full_build_path)
            need_build = True

            # Create all directories
            dirs = list_recursive_dirnames(self.source)
            if dirs:
                dirs_text = " ".join(dirs)
                fmt_arg = (self.full_build_path, self.full_build_path,
                           dirs_text)
                cmd = 'mkdir -p %s && cd %s && mkdir -p %s' % fmt_arg
            else:
                cmd = 'mkdir -p %s' % self.full_build_path
            status, output = self.session.cmd_status_output(cmd)
            if not status == 0:
                raise BuildError("Unable to create remote directories: '%s'"
                                 % output)

            # Copy files
            for file_name in to_transfer:
                local_path = os.path.join(self.source, file_name)
                remote_path = os.path.join(self.full_build_path, file_name)
                remote.copy_files_to(self.address, self.file_transfer_client,
                                     self.username, self.password,
                                     self.file_transfer_port, local_path,
                                     remote_path)

        else:
            logging.info("Directory %s on target already up-to-date" %
                         self.full_build_path)

        return need_build

    def make(self):
        """
        Execute make on the remote system
        """
        logging.info("Building in %s on target" % self.full_build_path)
        cmd = 'make -C %s %s' % (self.full_build_path, self.make_flags)
        status, output = self.session.cmd_status_output(cmd)
        if not status == 0:
            raise BuildError("Unable to make: '%s'" % output)

    def build(self):
        """
        Synchronize all files and execute 'make' on the remote system if
        needed.
        :returns: The path to the build directory on the remote machine
        """
        if self.sync_directories():
            self.make()

        return self.full_build_path
