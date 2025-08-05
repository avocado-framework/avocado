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
# Author: Yiqiao Pu <ypu@redhat.com>

__doc__ = """
Module to handle file and directory paths.
It provides functions to manipulate file and directory paths,
check permissions, and inspect files.
"""

import os
import stat
import tempfile
import urllib

#: The indicator for a script file, usually the first line of the file.
SHEBANG = "#!"


class CmdNotFoundError(Exception):
    """Indicates that the command was not found in the system after a search.

    :param cmd: String with the command.
    :param paths: List of paths where we looked after.
    """

    def __init__(self, cmd, paths):  # pylint: disable=W0231
        super()
        self.cmd = cmd
        self.paths = paths

    def __str__(self):
        """String representation of the exception.

        :return: A string describing the missing command and the paths searched.
        :rtype: str
        """
        return (
            f"Command '{self.cmd}' could not be found in any "
            f"of the PATH dirs: {self.paths}"
        )


def get_path(base_path, user_path):
    """Translate a user specified path to a real path.

    If user_path is relative, append it to base_path.
    If user_path is absolute, return it as is.

    :param base_path: The base path of relative user specified paths.
    :param type base_path: str
    :param user_path: The user specified path.
    :type user_path: str
    :return: The resolved path.
    :rtype: str
    """
    if os.path.isabs(user_path) or urllib.parse.urlparse(user_path)[0] in [
        "http",
        "https",
        "ftp",
        "file",
    ]:
        return user_path
    return os.path.join(base_path, user_path)


def init_dir(*args):
    """Wrapper around os.path.join that creates dirs based on the final path.

    :param args: List of dir arguments that will be os.path.joined.
    :return: directory.
    :rtype: str
    """
    directory = os.path.join(*args)
    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
    return directory


def find_command(cmd, default=None, check_exec=True):
    """Try to find a command in the PATH, paranoid version.

    :param cmd: Command to be found.
    :type cmd: str
    :param default: Command path to use as a fallback if not found
                    in the standard directories.
    :type default: str or None
    :param check_exec: if a check for permissions that render the command
                       executable by the current user should be performed.
    :type check_exec: bool
    :raise avocado.utils.path.CmdNotFoundError: in case the
            command was not found and no default was given.
    :return: Returns an absolute path to the command or the default
            value if the command is not found
    :rtype: str
    """
    common_bin_paths = [
        "/usr/libexec",
        "/usr/local/sbin",
        "/usr/local/bin",
        "/usr/sbin",
        "/usr/bin",
        "/sbin",
        "/bin",
    ]
    try:
        path_paths = os.environ["PATH"].split(":")
    except KeyError:
        path_paths = []
    path_paths = list(set(common_bin_paths + path_paths))

    for dir_path in path_paths:
        cmd_path = os.path.join(dir_path, cmd)
        if os.path.isfile(cmd_path):
            if check_exec:
                if not os.access(cmd_path, os.R_OK | os.X_OK):
                    continue
            return os.path.abspath(cmd_path)

    if default is not None:
        return default
    path_paths.sort()
    raise CmdNotFoundError(cmd, path_paths)


class PathInspector:
    """Inspects paths to provide information about them.

    :param path: The path to inspect.
    :type path: str
    """

    def __init__(self, path):
        self.path = path

    def get_first_line(self):
        """Reads and returns the first line of the file from path.

        :return: The first line of the file or an empty string if the file
                 does not exist or is empty.
        :rtype: str
        """
        first_line = ""
        if os.path.isfile(self.path):
            with open(self.path, "r", encoding="utf-8") as open_file:
                first_line = open_file.readline()
        return first_line

    def has_exec_permission(self):
        """Checks if the file from path has execute permissions for the user.

        :return: True if the file has execute permissions, False otherwise.
        :rtype: bool
        """
        if os.path.exists(self.path):
            mode = os.stat(self.path)[stat.ST_MODE]
            return mode & stat.S_IXUSR
        return False

    def is_empty(self):
        """Checks if the file in path is empty.

        :return: True if the file is empty, False otherwise.
        :rtype: bool
        """
        if os.path.exists(self.path):
            size = os.stat(self.path)[stat.ST_SIZE]
            return not size
        return False

    def is_script(self, language=None):
        """Checks if the file in the path is a script, optionally checking for a specific language.

        :param language: The scripting language to check for (e.g., "python").
                         If None, checks for any shebang.
        :type language: str, optional
        :return: True if the file is a script (and matches the language, if provided),
                 False otherwise.
        :rtype: bool
        """
        first_line = self.get_first_line()
        if first_line:
            if first_line.startswith(SHEBANG):
                if language is None:
                    return True
                if language in first_line:
                    return True
        return False

    def is_python(self):
        """Checks if the file in path is a Python script.

        :return: True if the file is a Python script, False otherwise.
        :rtype: bool
        """
        if self.path.endswith(".py"):
            return True
        return self.is_script(language="python")


def usable_rw_dir(directory, create=True):
    """Verify whether we can use this dir (read/write).

    Checks for appropriate permissions, and creates missing dirs as needed.

    :param directory: Directory to check.
    :type directory: str
    :param create: whether to create the directory if it does not exist.
    :type create: bool
    :return: True if the directory is usable for rw, False otherwise.
    :rtype: bool
    """
    if os.path.isdir(directory):
        try:
            fd, path = tempfile.mkstemp(dir=directory)
            os.close(fd)
            os.unlink(path)
            return True
        except OSError:
            pass
    elif create:
        try:
            init_dir(directory)
            return True
        except OSError:
            pass

    return False


def usable_ro_dir(directory):
    """Verify whether dir exists and we can access its contents.

    Check if a usable RO directory is there.

    :param directory: Directory to check.
    :type directory: str
    :return: True if the directory is accessible, False otherwise.
    :rtype: bool
    """
    try:
        cwd = os.getcwd()
    except FileNotFoundError:
        return False

    if os.path.isdir(directory):
        try:
            os.chdir(directory)
            os.chdir(cwd)
            return True
        except OSError:
            pass

    return False


def check_readable(path):
    """Verify that the given path exists and is readable.

    This should be used where an assertion makes sense, and is useful
    because it can provide a better message in the exception it
    raises.

    :param path: the path to test
    :type path: str
    :raise OSError: path does not exist or path could not be read
    """
    if not os.path.exists(path):
        raise OSError(f'File "{path}" does not exist')
    if not os.access(path, os.R_OK):
        raise OSError(f'File "{path}" can not be read')


def get_path_mount_point(path):
    """Returns the mount point for a given file path.

    :param path: the complete filename path. if a non-absolute path is
                 given, it's transformed into an absolute path first.
    :type path: str
    :returns: the mount point for a given file path
    :rtype: str
    """
    path = os.path.abspath(path)
    while not os.path.ismount(path):
        path = os.path.dirname(path)
    return path


def get_max_file_name_length(path):
    """Returns the maximum length of a file name in the underlying file system.

    :param path: the complete filename path. if a non-absolute path is
                 given, it's transformed into an absolute path first.
    :type path: str
    :returns: the maximum length of a file name
    :rtype: int
    """
    if hasattr(os, "pathconf"):
        mount_point = get_path_mount_point(path)
        return os.pathconf(mount_point, "PC_NAME_MAX")
    # Given the unavailability of os.pathconf(), always available
    # under Unix, it should be safe to assume this is Windows.
    # About Windows, versions and configurations can yield different
    # file name length limits.  The value hardcoded here (248) is
    # calculated from the 260 MAX_PATH limit, plus the provision
    # for directories names allowing a 8.3 filename inside it.
    return 248
