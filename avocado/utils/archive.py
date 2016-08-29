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
Module to help extract and create compressed archives.
"""

import logging
import os
import platform
import stat
import tarfile
import zipfile


LOG = logging.getLogger(__name__)


try:
    import lzma
    LZMA_CAPABLE = True
except ImportError:
    LZMA_CAPABLE = False


class ArchiveException(Exception):

    """
    Base exception for all archive errors.
    """
    pass


class _WrapLZMA(object):

    """ wraps tar.xz for python 2.7's tarfile """

    def __init__(self, filename, mode):
        """
        Creates an instance of :class:`ArchiveFile`.

        :param filename: the archive file name.
        :param mode: file mode, `r` read, `w` write.
        """
        self._engine = tarfile.open(fileobj=lzma.LZMAFile(filename, mode),
                                    mode=mode)
        methods = dir(self._engine)
        for meth in dir(self):
            try:
                methods.remove(meth)
            except ValueError:
                pass
        for method in methods:
            setattr(self, method, getattr(self._engine, method))

    @classmethod
    def open(cls, filename, mode='r'):
        """
        Creates an instance of :class:`_WrapLZMA`.

        :param filename: the archive file name.
        :param mode: file mode, `r` read, `w` write.
        """
        return cls(filename, mode)


class ArchiveFile(object):

    """
    Class that represents an Archive file.

    Archives are ZIP files or Tarballs.
    """

    # extension info: is_zip, is_tar, zipfile|tarfile, +mode
    _extension_table = {
        '.zip': (True, False, zipfile.ZipFile, ''),
        '.tar': (False, True, tarfile.open, ''),
        '.tar.gz': (False, True, tarfile.open, ':gz'),
        '.tgz': (False, True, tarfile.open, ':gz'),
        '.tar.bz2': (False, True, tarfile.open, ':bz2'),
        '.tbz2': (False, True, tarfile.open, ':bz2')}

    if LZMA_CAPABLE:
        _extension_table['.xz'] = (False, True, _WrapLZMA.open, '')

    def __init__(self, filename, mode='r'):
        """
        Creates an instance of :class:`ArchiveFile`.

        :param filename: the archive file name.
        :param mode: file mode, `r` read, `w` write.
        """
        self.filename = filename
        self.mode = mode
        engine = None
        for ext in ArchiveFile._extension_table:
            if filename.endswith(ext):
                (self.is_zip,
                 self.is_tar,
                 engine,
                 extra_mode) = ArchiveFile._extension_table[ext]
        if engine is not None:
            self.mode += extra_mode
            self._engine = engine(self.filename, self.mode)
        else:
            raise ArchiveException('file is not an archive')

    def __repr__(self):
        return "ArchiveFile('%s', '%s')" % (self.filename, self.mode)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self._engine is not None:
            self.close()

    @classmethod
    def open(cls, filename, mode='r'):
        """
        Creates an instance of :class:`ArchiveFile`.

        :param filename: the archive file name.
        :param mode: file mode, `r` read, `w` write.
        """
        return cls(filename, mode)

    def add(self, filename, arcname=None):
        """
        Add file to the archive.

        :param filename: file to archive.
        :param arcname: alternative name for the file in the archive.
        """
        if self.is_zip:
            self._engine.write(filename, arcname, zipfile.ZIP_DEFLATED)
        else:
            self._engine.add(filename, arcname)

    def list(self):
        """
        List files to the standard output.
        """
        if self.is_zip:
            self._engine.printdir()
        else:
            self._engine.list()

    def extract(self, path='.'):
        """
        Extract all files from the archive.

        :param path: destination path.
        """
        self._engine.extractall(path)
        if self.is_zip:
            self._update_zip_extra_attrs(path)

    def _update_zip_extra_attrs(self, dst_dir):
        if platform.system() != "Linux":
            LOG.warn("Attr handling in zip files only supported on Linux.")
            return
        # Walk all files and re-create files as symlinks
        for path, info in self._engine.NameToInfo.iteritems():
            dst = os.path.join(dst_dir, path)
            if not os.path.exists(dst):
                LOG.warn("One or more files in the ZIP archive '%s' could "
                         "not be found after extraction. Their paths are "
                         "probably stored in unsupported format and their "
                         "attributes are not going to be updated",
                         self.filename)
                return
            attr = info.external_attr >> 16
            if attr & stat.S_IFLNK == stat.S_IFLNK:
                dst = os.path.join(dst_dir, path)
                src = open(dst, 'r').read()
                os.remove(dst)
                os.symlink(src, dst)
                continue    # Don't override any other attributes on links
            mode = attr & 511   # Mask only permissions
            if mode and mode != 436:  # If mode is stored and is not default
                os.chmod(dst, mode)

    def close(self):
        """
        Close archive.
        """
        self._engine.close()


def is_archive(filename):
    """
    Test if a given file is an archive.

    :param filename: file to test.
    :return: `True` if it is an archive.
    """
    return zipfile.is_zipfile(filename) or tarfile.is_tarfile(filename)


def compress(filename, path):
    """
    Compress files in an archive.

    :param filename: archive file name.
    :param path: origin directory path to files to compress. No
                 individual files allowed.
    """
    with ArchiveFile.open(filename, 'w') as x:
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for name in files:
                    newroot = root.replace(path, '')
                    x.add(os.path.join(root, name),
                          os.path.join(newroot, name))
        elif os.path.isfile(path):
            x.add(path, os.path.basename(path))


def uncompress(filename, path):
    """
    Extract files from an archive.

    :param filename: archive file name.
    :param path: destination path to extract to.
    """
    with ArchiveFile.open(filename) as x:
        x.extract(path)

# Some aliases
create = compress
extract = uncompress
