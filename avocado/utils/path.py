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

from avocado.utils import aurl


PY_EXTENSIONS = ['.py']
SHEBANG = '#!'


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


class PathInspector(object):

    def __init__(self, path):
        self.path = path

    def get_first_line(self):
        first_line = ""
        if os.path.isfile(self.path):
            checked_file = open(self.path, "r")
            first_line = checked_file.readline()
            checked_file.close()
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
        for extension in PY_EXTENSIONS:
            if self.path.endswith(extension):
                return True

        return self.is_script(language='python')
