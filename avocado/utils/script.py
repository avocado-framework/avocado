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
# Copyright: Red Hat Inc. 2014
# Author: Ruda Moura <rmoura@redhat.com>

"""
Module to handle scripts creation.
"""

import os
import shutil
import stat
import tempfile

from . import path as utils_path

#: What is commonly known as "0775" or "u=rwx,g=rwx,o=rx"
DEFAULT_MODE = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP |
                stat.S_IROTH | stat.S_IXOTH)

#: What is commonly known as "0444" or "u=r,g=r,o=r"
READ_ONLY_MODE = (stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


class Script:

    """
    Class that represents a script.
    """

    def __init__(self, path, content, mode=DEFAULT_MODE, open_mode='w'):
        """
        Creates an instance of :class:`Script`.

        Note that when the instance inside a with statement, it will
        automatically call save() and then remove() for you.

        :param path: the script file name.
        :param content: the script content.
        :param mode: set file mode, defaults what is commonly known as 0775.
        """
        self.path = path
        self.content = content
        self.mode = mode
        self.stored = False
        self.open_mode = open_mode

    def __repr__(self):
        return '%s(path="%s", stored=%s)' % (self.__class__.__name__,
                                             self.path,
                                             self.stored)

    def __str__(self):
        return self.path

    def __enter__(self):
        self.save()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.remove()

    def save(self):
        """
        Store script to file system.

        :return: `True` if script has been stored, otherwise `False`.
        """
        dirname = os.path.dirname(self.path)
        utils_path.init_dir(dirname)
        with open(self.path, self.open_mode) as fd:
            fd.write(self.content)
            os.chmod(self.path, self.mode)
            self.stored = True
        return self.stored

    def remove(self):
        """
        Remove script from the file system.

        :return: `True` if script has been removed, otherwise `False`.
        """
        if os.path.exists(self.path):
            os.remove(self.path)
            self.stored = False
            return True
        else:
            return False


class TemporaryScript(Script):

    """
    Class that represents a temporary script.
    """

    def __init__(self, name, content, prefix='avocado_script', mode=DEFAULT_MODE, open_mode='w'):
        """
        Creates an instance of :class:`TemporaryScript`.

        Note that when the instance inside a with statement, it will
        automatically call save() and then remove() for you.

        When the instance object is garbage collected, it will automatically
        call remove() for you.

        :param name: the script file name.
        :param content: the script content.
        :param prefix: prefix for the temporary directory name.
        :param mode: set file mode, default to 0775.
        """
        tmpdir = tempfile.mkdtemp(prefix=prefix)
        super(TemporaryScript, self).__init__(os.path.join(tmpdir, name),
                                              content, mode, open_mode)

    def __del__(self):
        self.remove()

    def remove(self):
        if os.path.exists(os.path.dirname(self.path)):
            shutil.rmtree(os.path.dirname(self.path))
            self.stored = False


def make_script(path, content, mode=DEFAULT_MODE):
    """
    Creates a new script stored in the file system.

    :param path: the script file name.
    :param content: the script content.
    :param mode: set file mode, default to 0775.
    :return: the script path.
    """
    scpt = Script(path, content, mode=mode)
    scpt.save()
    return scpt.path


def make_temp_script(name, content, prefix='avocado_script', mode=DEFAULT_MODE):
    """
    Creates a new temporary script stored in the file system.

    :param path: the script file name.
    :param content: the script content.
    :param prefix: the directory prefix Default to 'avocado_script'.
    :param mode: set file mode, default to 0775.
    :return: the script path.
    """
    scpt = TemporaryScript(name, content, prefix=prefix, mode=mode)
    scpt.save()
    return scpt.path
