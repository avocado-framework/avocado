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
import tempfile


class Script(object):

    """
    Class that represents a script.
    """

    def __init__(self, path, content, mode=0775):
        """
        Creates an instance of :class:`Script`.

        :param path: the script file name.
        :param content: the script content.
        :param mode: set file mode, default to 0775.
        """
        self.path = path
        self.content = content
        self.mode = mode
        self.stored = False

    def __repr__(self):
        return '%s(path="%s", stored=%s)' % (self.__class__.__name__,
                                             self.path,
                                             self.stored)

    def __str__(self):
        return self.path

    def save(self):
        """
        Store script to file system.

        :return: `True` if script has been stored, otherwise `False`.
        """
        if not os.path.isdir(os.path.dirname(self.path)):
            os.makedirs(os.path.dirname(self.path))
        with open(self.path, 'w') as fd:
            fd.write(self.content)
            os.chmod(self.path, self.mode)
            self.stored = True
        return self.stored

    def remove(self):
        """
        Remove script from file system.

        :return: `True` if script has been removed, otherwise `False`.
        """
        if self.stored:
            os.remove(self.path)
            self.stored = False
            return True
        else:
            return False


class TemporaryScript(Script):

    """
    Class that represents a temporary script.
    """

    def __init__(self, name, content, prefix='avocado_script', mode=0775):
        """
        Creates an instance of :class:`TemporaryScript`.

        :param name: the script file name.
        :param content: the script content.
        :param prefix: prefix for the temporary directory name.
        :param mode: set file mode, default to 0775.
        """
        tmpdir = tempfile.mkdtemp(prefix=prefix)
        self.path = os.path.join(tmpdir, name)
        self.content = content
        self.mode = mode
        self.stored = False


def make_script(path, content, mode=0775):
    """
    Creates a new script stored in the file system.

    :param path: the script file name.
    :param contet: the script content.
    :param mode: set file mode, default to 0775.
    :return: the script path.
    """
    scpt = Script(path, content, mode=mode)
    scpt.save()
    return scpt.path


def make_temp_script(name, content, prefix='avocado_script', mode=0775):
    """
    Creates a new temporary script stored in the file system.

    :param path: the script file name.
    :param contet: the script content.
    :param prefix: the directory prefix Default to 'avocado_script'.
    :param mode: set file mode, default to 0775.
    :return: the script path.
    """
    scpt = TemporaryScript(name, content, prefix=prefix, mode=mode)
    scpt.save()
    return scpt.path
