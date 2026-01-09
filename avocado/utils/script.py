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

"""Module to handle script file creation and management.

This module provides utilities for creating executable script files,
both permanent and temporary, with proper file permissions and
automatic cleanup capabilities.
"""

import os
import shutil
import stat
import tempfile

from avocado.utils import path as utils_path

#: What is commonly known as "0775" or "u=rwx,g=rwx,o=rx"
DEFAULT_MODE = (
    stat.S_IRUSR
    | stat.S_IWUSR
    | stat.S_IXUSR
    | stat.S_IRGRP
    | stat.S_IWGRP
    | stat.S_IXGRP
    | stat.S_IROTH
    | stat.S_IXOTH
)

#: What is commonly known as "0444" or "u=r,g=r,o=r"
READ_ONLY_MODE = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH


class Script:
    """Class that represents a script file.

    This class provides methods to create, save, and remove script files
    with configurable permissions. It supports context manager protocol
    for automatic cleanup.
    """

    def __init__(self, path, content, mode=DEFAULT_MODE, open_mode="w"):
        """Creates an instance of :class:`Script`.

        When used as a context manager, the script is automatically saved
        on entry and removed on exit.

        :param path: The path where the script file will be created.
        :type path: str
        :param content: The content to write to the script file.
        :type content: str or bytes
        :param mode: File permissions mode. Defaults to 0775 (rwxrwxr-x).
        :type mode: int
        :param open_mode: File open mode ('w' for text, 'wb' for binary).
        :type open_mode: str
        """
        self.path = path
        self.content = content
        self.mode = mode
        self.stored = False
        self.open_mode = open_mode

    def __repr__(self):
        return (
            f'{self.__class__.__name__}(path="{self.path}", ' f"stored={self.stored})"
        )

    def __str__(self):
        return self.path

    def __enter__(self):
        self.save()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.remove()

    def save(self):
        """Store script content to the file system.

        Creates parent directories if they do not exist and sets the
        specified file permissions.

        :return: True if script has been stored successfully.
        :rtype: bool
        """
        dirname = os.path.dirname(self.path)
        utils_path.init_dir(dirname)
        with open(self.path, self.open_mode) as fd:  # pylint: disable=W1514
            fd.write(self.content)
            os.chmod(self.path, self.mode)
            self.stored = True
        return self.stored

    def remove(self):
        """Remove script file from the file system.

        :return: True if the script file was removed, False if it did not exist.
        :rtype: bool
        """
        if os.path.exists(self.path):
            os.remove(self.path)
            self.stored = False
            return True
        return False


class TemporaryScript(Script):
    """Class that represents a temporary script in an auto-managed directory.

    The script is created in a temporary directory that is automatically
    cleaned up when the instance is garbage collected or when used as
    a context manager.
    """

    # pylint: disable=R0913
    def __init__(
        self, name, content, prefix="avocado_script", mode=DEFAULT_MODE, open_mode="w"
    ):
        """Creates an instance of :class:`TemporaryScript`.

        The script is created in a newly created temporary directory. When
        used as a context manager, both the script and its directory are
        automatically removed on exit. The directory is also removed when
        the object is garbage collected.

        :param name: The script filename (not the full path).
        :type name: str
        :param content: The content to write to the script file.
        :type content: str or bytes
        :param prefix: Prefix for the temporary directory name.
        :type prefix: str
        :param mode: File permissions mode. Defaults to 0775 (rwxrwxr-x).
        :type mode: int
        :param open_mode: File open mode ('w' for text, 'wb' for binary).
        :type open_mode: str
        """
        tmpdir = tempfile.mkdtemp(prefix=prefix)
        super().__init__(os.path.join(tmpdir, name), content, mode, open_mode)

    def __del__(self):
        self.remove()

    def remove(self):
        if os.path.exists(os.path.dirname(self.path)):
            shutil.rmtree(os.path.dirname(self.path))
            self.stored = False


def make_script(path, content, mode=DEFAULT_MODE):
    """Creates and saves a new script file to the file system.

    This is a convenience function that creates a Script instance,
    saves it, and returns the path.

    :param path: The path where the script file will be created.
    :type path: str
    :param content: The content to write to the script file.
    :type content: str or bytes
    :param mode: File permissions mode. Defaults to 0775 (rwxrwxr-x).
    :type mode: int
    :return: The path to the created script file.
    :rtype: str
    """
    scpt = Script(path, content, mode=mode)
    scpt.save()
    return scpt.path


def make_temp_script(name, content, prefix="avocado_script", mode=DEFAULT_MODE):
    """Creates and saves a new temporary script in a temporary directory.

    This is a convenience function that creates a TemporaryScript instance
    and saves it. Note that the script's temporary directory will be removed
    when the TemporaryScript object is garbage collected.

    :param name: The script filename (not the full path).
    :type name: str
    :param content: The content to write to the script file.
    :type content: str or bytes
    :param prefix: Prefix for the temporary directory name.
    :type prefix: str
    :param mode: File permissions mode. Defaults to 0775 (rwxrwxr-x).
    :type mode: int
    :return: The full path to the created script file.
    :rtype: str
    """
    scpt = TemporaryScript(name, content, prefix=prefix, mode=mode)
    scpt.save()
    return scpt.path


# pylint: disable=wrong-import-position
from avocado.utils.deprecation import log_deprecation

log_deprecation.warning("script")
