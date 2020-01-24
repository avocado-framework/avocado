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

"""
Avocado path related functions.
"""

import os
import stat
import tempfile

from . import aurl

SHEBANG = '#!'


class CmdNotFoundError(Exception):

    """
    Indicates that the command was not found in the system after a search.

    :param cmd: String with the command.
    :param paths: List of paths where we looked after.
    """

    def __init__(self, cmd, paths):  # pylint: disable=W0231
        super(CmdNotFoundError, self)
        self.cmd = cmd
        self.paths = paths

    def __str__(self):
        return ("Command '%s' could not be found in any of the PATH dirs: %s" %
                (self.cmd, self.paths))


def get_path(base_path, user_path):
    """
    Translate a user specified path to a real path.
    If user_path is relative, append it to base_path.
    If user_path is absolute, return it as is.

    :param base_path: The base path of relative user specified paths.
    :param user_path: The user specified path.
    """
    if os.path.isabs(user_path) or aurl.is_url(user_path):
        return user_path
    else:
        return os.path.join(base_path, user_path)


def init_dir(*args):
    """
    Wrapper around os.path.join that creates dirs based on the final path.

    :param args: List of dir arguments that will be os.path.joined.
    :type directory: list
    :return: directory.
    :rtype: str
    """
    directory = os.path.join(*args)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    return directory


def find_command(cmd, default=None, check_exec=True):
    """
    Try to find a command in the PATH, paranoid version.

    :param cmd: Command to be found.
    :param default: Command path to use as a fallback if not found
                    in the standard directories.
    :param check_exec: if a check for permissions that render the command
                       executable by the current user should be performed.
    :type check_exec: bool
    :raise: :class:`avocado.utils.path.CmdNotFoundError` in case the
            command was not found and no default was given.
    :return: Returns an absolute path to the command or the default
            value if the command is not found
    :rtype: str
    """
    common_bin_paths = ["/usr/libexec", "/usr/local/sbin", "/usr/local/bin",
                        "/usr/sbin", "/usr/bin", "/sbin", "/bin"]
    try:
        path_paths = os.environ['PATH'].split(":")
    except IndexError:
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
    else:
        path_paths.sort()
        raise CmdNotFoundError(cmd, path_paths)


class PathInspector:

    def __init__(self, path):
        self.path = path

    def get_first_line(self):
        first_line = ""
        if os.path.isfile(self.path):
            with open(self.path, 'r') as open_file:
                first_line = open_file.readline()
        return first_line

    def has_exec_permission(self):
        mode = os.stat(self.path)[stat.ST_MODE]
        return mode & stat.S_IXUSR

    def is_empty(self):
        size = os.stat(self.path)[stat.ST_SIZE]
        return size == 0

    def is_script(self, language=None):
        first_line = self.get_first_line()
        if first_line:
            if first_line.startswith(SHEBANG):
                if language is None:
                    return True
                elif language in first_line:
                    return True
        return False

    def is_python(self):
        if self.path.endswith('.py'):
            return True
        return self.is_script(language='python')


def usable_rw_dir(directory, create=True):
    """
    Verify whether we can use this dir (read/write).

    Checks for appropriate permissions, and creates missing dirs as needed.

    :param directory: Directory
    :param create: whether to create the directory
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
    """
    Verify whether dir exists and we can access its contents.

    Check if a usable RO directory is there.

    :param directory: Directory
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
    """
    Verify that the given path exists and is readable

    This should be used where an assertion makes sense, and is useful
    because it can provide a better message in the exception it
    raises.

    :param path: the path to test
    :type path: str
    :raise OSError: path does not exist or path could not be read
    :rtype: None
    """
    if not os.path.exists(path):
        raise OSError('File "%s" does not exist' % path)
    if not os.access(path, os.R_OK):
        raise OSError('File "%s" can not be read' % path)
