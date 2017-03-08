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


__all__ = ['iso9660', 'Iso9660IsoInfo', 'Iso9660IsoRead', 'Iso9660Mount']

import os
import logging
import tempfile
import shutil
import sys
import re

from . import process


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


def can_mount():
    """
    Test whether the current user can perform a loop mount

    AFAIK, this means being root, having mount and iso9660 kernel support

    :rtype: bool
    """
    if not process.can_sudo():
        logging.debug('Can not use mount: current user is not "root" and'
                      "sudo is not configured.")
        return False

    if not has_userland_tool('mount'):
        logging.debug('Can not use mount: missing "mount" tool')
        return False

    if 'iso9660' not in open('/proc/filesystems').read():
        process.system("modprobe iso9660", ignore_status=True, sudo=True)
        if 'iso9660' not in open('/proc/filesystems').read():
            logging.debug('Can not use mount: lack of iso9660 kernel support')
            return False

    return True


class BaseIso9660(object):

    """
    Represents a ISO9660 filesystem

    This class holds common functionality and has many abstract methods
    """

    def __init__(self, path):
        self.path = path
        self._verify_path(path)

    @staticmethod
    def _verify_path(path):
        """
        Verify that the current set path is accessible

        :param path: the path for test
        :type path: str
        :raise OSError: path does not exist or path could not be read
        :rtype: None
        """
        if not os.path.exists(path):
            raise OSError('File or device path does not exist: %s' %
                          path)
        if not os.access(path, os.R_OK):
            raise OSError('File or device path could not be read: %s' %
                          path)

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
        output = open(dst, 'w+b')
        output.write(content)
        output.close()

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
        pass


class MixInMntDirMount(object):
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
                raise RuntimeError("Path to iso image not available: %s"
                                   % self.path)
            self._mount_instance = Iso9660Mount(self.path)
        return self._mount_instance.mnt_dir

    def close(self):
        """
        Cleanups and frees any resources being used
        """
        super(MixInMntDirMount, self).close()
        if self._mount_instance:
            self._mount_instance.close()
            self._mount_instance = None


class Iso9660IsoInfo(MixInMntDirMount, BaseIso9660):

    """
    Represents a ISO9660 filesystem

    This implementation is based on the cdrkit's isoinfo tool
    """

    def __init__(self, path):
        super(Iso9660IsoInfo, self).__init__(path)
        self.joliet = False
        self.rock_ridge = False
        self.el_torito = False
        self._get_extensions(path)

    def _get_extensions(self, path):
        """
        Get and store the image's extensions
        """
        cmd = 'isoinfo -i %s -d' % path
        output = process.system_output(cmd)

        if re.findall("\nJoliet", output):
            self.joliet = True
        if re.findall("\nRock Ridge signatures", output):
            self.rock_ridge = True
        if re.findall("\nEl Torito", output):
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
        cmd = 'isoinfo -i %s -f' % self.path
        flist = process.system_output(cmd)

        fname = re.findall("(%s.*)" % self._normalize_path(path), flist, re.I)
        if fname:
            return fname[0]
        return None

    def read(self, path):
        cmd = ['isoinfo', '-i %s' % self.path]

        fname = self._normalize_path(path)
        if self.joliet:
            cmd.append("-J")
        elif self.rock_ridge:
            cmd.append("-R")
        else:
            fname = self._get_filename_in_iso(path)
            if not fname:
                logging.warn(
                    "Could not find '%s' in iso '%s'", path, self.path)
                return ""

        cmd.append("-x %s" % fname)
        result = process.run(" ".join(cmd), verbose=False)
        return result.stdout


class Iso9660IsoRead(MixInMntDirMount, BaseIso9660):

    """
    Represents a ISO9660 filesystem

    This implementation is based on the libcdio's iso-read tool
    """

    def __init__(self, path):
        super(Iso9660IsoRead, self).__init__(path)
        self.temp_dir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def read(self, path):
        temp_file = os.path.join(self.temp_dir, path)
        cmd = 'iso-read -i %s -e %s -o %s' % (self.path, path, temp_file)
        process.run(cmd)
        return open(temp_file).read()

    def copy(self, src, dst):
        cmd = 'iso-read -i %s -e %s -o %s' % (self.path, src, dst)
        process.run(cmd)

    def close(self):
        super(Iso9660IsoRead, self).close()
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
        super(Iso9660Mount, self).__init__(path)
        self._mnt_dir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        if sys.platform.startswith('darwin'):
            fs_type = 'cd9660'
        else:
            fs_type = 'iso9660'
        process.run('mount -t %s -v -o loop,ro %s %s' %
                    (fs_type, path, self.mnt_dir), sudo=True)

    def read(self, path):
        """
        Read data from path

        :param path: path to read data
        :type path: str
        :return: data content
        :rtype: str
        """
        full_path = os.path.join(self.mnt_dir, path)
        return open(full_path).read()

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
                process.run('fuser -k %s' % self.mnt_dir, ignore_status=True,
                            sudo=True)
                process.run('umount %s' % self.mnt_dir, sudo=True)
            shutil.rmtree(self._mnt_dir)
            self._mnt_dir = None

    @property
    def mnt_dir(self):
        if not self._mnt_dir:
            raise RuntimeError("Trying to get mnt_dir of already closed iso %s"
                               % self.path)
        return self._mnt_dir


def iso9660(path):
    """
    Checks the available tools on a system and chooses class accordingly

    This is a convenience function, that will pick the first available
    iso9660 capable tool.

    :param path: path to an iso9660 image file
    :type path: str
    :return: an instance of any iso9660 capable tool
    :rtype: :class:`Iso9660IsoInfo`, :class:`Iso9660IsoRead`,
            :class:`Iso9660Mount` or None
    """
    implementations = [('isoinfo', has_isoinfo, Iso9660IsoInfo),
                       ('iso-read', has_isoread, Iso9660IsoRead),
                       ('mount', can_mount, Iso9660Mount)]

    for (name, check, klass) in implementations:
        if check():
            logging.debug('Automatically chosen class for iso9660: %s', name)
            return klass(path)

    return None
