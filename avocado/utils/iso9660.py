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
# Copyright: Red Hat Inc. 2015
# Author: Cleber Rosa <crosa@redhat.com>

"""
Basic ISO9660 file-system support.

This code does not attempt (so far) to implement code that knows about
ISO9660 internal structure. Instead, it uses commonly available support
either in userspace tools or on the Linux kernel itself (via mount).
"""


__all__ = ['iso9660', 'Iso9660IsoInfo', 'Iso9660IsoRead', 'Iso9660Mount',
           'ISO9660PyCDLib']

import io
import logging
import os
import re
import shutil
import string
import sys
import tempfile

from avocado.utils import process

try:
    import pycdlib
except ImportError:
    pycdlib = None

LOG = logging.getLogger(__name__)


def has_userland_tool(executable):
    """
    Returns whether the system has a given executable

    :param executable: the name of the executable
    :type executable: str
    :rtype: bool
    """
    if os.path.isabs(executable):
        return os.path.exists(executable)
    else:
        for path in os.environ['PATH'].split(':'):
            if os.path.exists(os.path.join(path, executable)):
                return True
    return False


def has_isoinfo():
    """
    Returns whether the system has the isoinfo executable

    Maybe more checks could be added to see if isoinfo supports the needed
    features

    :rtype: bool
    """
    return has_userland_tool('isoinfo')


def has_isoread():
    """
    Returns whether the system has the iso-read executable

    Maybe more checks could be added to see if iso-read supports the needed
    features

    :rtype: bool
    """
    return has_userland_tool('iso-read')


def has_pycdlib():
    """
    Returns whether the system has the Python "pycdlib" library

    :rtype: bool
    """
    return pycdlib is not None


def can_mount():
    """
    Test whether the current user can perform a loop mount

    AFAIK, this means being root, having mount and iso9660 kernel support

    :rtype: bool
    """
    if not process.can_sudo():
        LOG.debug('Can not use mount: current user is not "root" and '
                  'sudo is not configured.')
        return False

    if not has_userland_tool('mount'):
        LOG.debug('Can not use mount: missing "mount" tool')
        return False

    with open('/proc/filesystems') as proc_filesystems:  # pylint: disable=W1514
        if 'iso9660' not in proc_filesystems.read():
            process.system("modprobe iso9660", ignore_status=True, sudo=True)
    with open('/proc/filesystems') as proc_filesystems:  # pylint: disable=W1514
        if 'iso9660' not in proc_filesystems.read():
            LOG.debug('Can not use mount: lack of iso9660 kernel support')
            return False

    return True


class BaseIso9660:

    """
    Represents a ISO9660 filesystem

    This class holds common functionality and has many abstract methods
    """

    def __init__(self, path):
        self.path = path

    def read(self, path):
        """
        Abstract method to read data from path

        :param path: path to the file
        :returns: data content from the file
        :rtype: str
        """
        raise NotImplementedError

    def copy(self, src, dst):
        """
        Simplistic version of copy that relies on read()

        :param src: source path
        :type src: str
        :param dst: destination path
        :type dst: str
        :rtype: None
        """
        content = self.read(src)
        with open(dst, 'w+b') as output:
            output.write(content)

    @property
    def mnt_dir(self):
        """
        Returns a path to the browsable content of the iso
        """
        raise NotImplementedError

    def close(self):
        """
        Cleanup and free any resources being used

        :rtype: None
        """


class MixInMntDirMount:
    """
    Mix in class which defines `mnt_dir` property and instantiates the
    Iso9660Mount class to provide one. It requires `self.path` to store
    path to the target iso file.
    """
    _mount_instance = None
    path = None

    @property
    def mnt_dir(self):
        """
        Returns a path to the browsable content of the iso
        """
        if self._mount_instance is None:
            if not self.path:
                raise RuntimeError(f"Path to iso image not available: "
                                   f"{self.path}")
            self._mount_instance = Iso9660Mount(self.path)
        return self._mount_instance.mnt_dir

    def close(self):
        """
        Cleanups and frees any resources being used
        """
        super().close()
        if self._mount_instance:
            self._mount_instance.close()
            self._mount_instance = None


class Iso9660IsoInfo(MixInMntDirMount, BaseIso9660):

    """
    Represents a ISO9660 filesystem

    This implementation is based on the cdrkit's isoinfo tool
    """

    def __init__(self, path):
        super().__init__(path)
        self.joliet = False
        self.rock_ridge = False
        self.el_torito = False
        self._get_extensions(path)

    def _get_extensions(self, path):
        """
        Get and store the image's extensions
        """
        cmd = f'isoinfo -i {path} -d'
        output = process.system_output(cmd)
        if b"\nJoliet" in output:
            self.joliet = True
        if b"\nRock Ridge signatures" in output:
            self.rock_ridge = True
        if b"\nEl Torito" in output:
            self.el_torito = True

    @staticmethod
    def _normalize_path(path):
        """
        Normalize the path to match isoinfo notation
        """
        if not os.path.isabs(path):
            path = os.path.join('/', path)
        return path

    def _get_filename_in_iso(self, path):
        """
        Locate the path in the list of files inside the iso image
        """
        cmd = f'isoinfo -i {self.path} -f'
        flist = process.system_output(cmd)

        fname = re.findall(f"({self._normalize_path(path)}.*)", flist, re.I)
        if fname:
            return fname[0]
        return None

    def read(self, path):
        cmd = ['isoinfo', f'-i {self.path}']

        fname = self._normalize_path(path)
        if self.joliet:
            cmd.append("-J")
        elif self.rock_ridge:
            cmd.append("-R")
        else:
            fname = self._get_filename_in_iso(path)
            if not fname:
                LOG.warning(
                    "Could not find '%s' in iso '%s'", path, self.path)
                return ""

        cmd.append(f"-x {fname}")
        result = process.run(" ".join(cmd), verbose=False)
        return result.stdout


class Iso9660IsoRead(MixInMntDirMount, BaseIso9660):

    """
    Represents a ISO9660 filesystem

    This implementation is based on the libcdio's iso-read tool
    """

    def __init__(self, path):
        super().__init__(path)
        self.temp_dir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def read(self, path):
        temp_path = os.path.join(self.temp_dir, path)
        cmd = f'iso-read -i {self.path} -e {path} -o {temp_path}'
        process.run(cmd)
        with open(temp_path, 'rb') as temp_file:
            return bytes(temp_file.read())

    def copy(self, src, dst):
        cmd = f'iso-read -i {self.path} -e {src} -o {dst}'
        process.run(cmd)

    def close(self):
        super().close()
        shutil.rmtree(self.temp_dir, True)


class Iso9660Mount(BaseIso9660):

    """
    Represents a mounted ISO9660 filesystem.
    """

    def __init__(self, path):
        """
        initializes a mounted ISO9660 filesystem

        :param path: path to the ISO9660 file
        :type path: str
        """
        super().__init__(path)
        self._mnt_dir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        if sys.platform.startswith('darwin'):
            fs_type = 'cd9660'
        else:
            fs_type = 'iso9660'
        process.run(f'mount -t {fs_type} -v -o loop,ro {path} {self.mnt_dir}',
                    sudo=True)

    def read(self, path):
        """
        Read data from path

        :param path: path to read data
        :type path: str
        :return: data content
        :rtype: str
        """
        full_path = os.path.join(self.mnt_dir, path)
        with open(full_path, 'rb') as file_to_read:
            return bytes(file_to_read.read())

    def copy(self, src, dst):
        """
        :param src: source
        :type src: str
        :param dst: destination
        :type dst: str
        :rtype: None
        """
        full_path = os.path.join(self.mnt_dir, src)
        shutil.copy(full_path, dst)

    def close(self):
        """
        Perform umount operation on the temporary dir

        :rtype: None
        """
        if self._mnt_dir:
            if os.path.ismount(self._mnt_dir):
                process.run(f'fuser -k {self.mnt_dir}', ignore_status=True,
                            sudo=True)
                process.run(f'umount {self.mnt_dir}', sudo=True)
            shutil.rmtree(self._mnt_dir)
            self._mnt_dir = None

    @property
    def mnt_dir(self):
        if not self._mnt_dir:
            raise RuntimeError(f"Trying to get mnt_dir of already closed "
                               f"iso {self.path}")
        return self._mnt_dir


class ISO9660PyCDLib(MixInMntDirMount, BaseIso9660):

    """
    Represents a ISO9660 filesystem

    This implementation is based on the pycdlib library
    """

    #: Default flags used when creating a new ISO image
    DEFAULT_CREATE_FLAGS = {"interchange_level": 3,
                            "joliet": 3}

    def __init__(self, path):
        if not has_pycdlib():
            raise RuntimeError('This class requires the pycdlib library')
        super().__init__(path)
        self._iso = None
        self._iso_opened_for_create = False

    def _open_for_read(self):
        if self._iso is None:
            self._iso = pycdlib.PyCdlib()
            self._iso.open(self.path)

    def create(self, flags=None):
        """
        Creates a new ISO image

        :param flags: the flags used when creating a new image
        :type flags: dict
        """
        if self._iso is None:
            self._iso = pycdlib.PyCdlib()
            if flags is None:
                flags = self.DEFAULT_CREATE_FLAGS
            self._iso.new(**flags)
            self._iso_opened_for_create = True

    @staticmethod
    def _get_iso_path(path):
        iso_path = "".join([c for c in path
                            if c in (string.ascii_letters + string.digits)])
        iso_path = iso_path[:7].upper() + ";"
        if not os.path.isabs(iso_path):
            iso_path = '/' + iso_path[:6] + ";"
        return iso_path

    @staticmethod
    def _get_abs_path(path):
        if not os.path.isabs(path):
            path = '/' + path
        return path

    def write(self, path, content):
        """
        Writes a new file into the ISO image

        :param path: the path of the new file inside the ISO image
        :type path: str
        :param content: the content of the new file
        :type path: bytes
        """
        self.create()
        self._iso.add_fp(io.BytesIO(content), len(content),
                         iso_path=self._get_iso_path(path),
                         joliet_path=self._get_abs_path(path))

    def read(self, path):
        self._open_for_read()
        if not os.path.isabs(path):
            path = '/' + path
        data = io.BytesIO()
        self._iso.get_file_from_iso_fp(data, joliet_path=path)
        return data.getvalue()

    def copy(self, src, dst):
        self._open_for_read()
        if not os.path.isabs(src):
            src = '/' + src
        self._iso.get_file_from_iso(dst, joliet_path=src)

    def close(self):
        super().close()
        if self._iso:
            if self._iso_opened_for_create:
                self._iso.write(self.path)
            self._iso.close()
            self._iso = None


def iso9660(path, capabilities=None):
    """
    Checks the available tools on a system and chooses class accordingly

    This is a convenience function, that will pick the first available
    iso9660 capable tool.

    :param path: path to an iso9660 image file
    :type path: str
    :param capabilities: list of specific capabilities that are
                         required for the selected implementation,
                         such as "read", "copy" and "mnt_dir".
    :type capabilities: list
    :return: an instance of any iso9660 capable tool
    :rtype: :class:`Iso9660IsoInfo`, :class:`Iso9660IsoRead`,
            :class:`Iso9660Mount`, :class:`ISO9660PyCDLib` or None
    """
    # all implementations so far have these base capabilities
    common_capabilities = ["read", "copy", "mnt_dir"]

    implementations = [('pycdlib', has_pycdlib, ISO9660PyCDLib,
                        common_capabilities + ["create", "write"]),

                       ('isoinfo', has_isoinfo, Iso9660IsoInfo,
                        common_capabilities),

                       ('iso-read', has_isoread, Iso9660IsoRead,
                        common_capabilities),

                       ('mount', can_mount, Iso9660Mount,
                        common_capabilities)]

    for (name, check, klass, cap) in implementations:
        if capabilities is not None and not set(capabilities).issubset(cap):
            continue
        if check():
            LOG.debug('Automatically chosen class for iso9660: %s', name)
            return klass(path)

    return None
