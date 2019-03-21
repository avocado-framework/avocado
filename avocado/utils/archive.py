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

import gzip
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
    try:
        from backports import lzma
        LZMA_CAPABLE = True
    except ImportError:
        LZMA_CAPABLE = False


#: The first two bytes that all gzip files start with
GZIP_MAGIC = b'\037\213'


def is_gzip_file(path):
    """
    Checks if file given by path has contents that suggests gzip file
    """
    with open(path, 'rb') as gzip_file:
        return gzip_file.read(len(GZIP_MAGIC)) == GZIP_MAGIC


def gzip_uncompress(path, output_path):
    """
    Uncompress a gzipped file at path, to either a file or dir at output_path
    """
    with gzip.GzipFile(filename=path, mode='rb') as input_file:
        if os.path.isdir(output_path):
            basename = os.path.basename(path)
            if basename.endswith('.gz'):
                basename = basename[:-3]
            output_path = os.path.join(output_path, basename)
        with open(output_path, 'wb') as output_file:
            while True:
                chunk = input_file.read(4096)
                if not chunk:
                    break
                output_file.write(chunk)
        return output_path


class ArchiveException(Exception):
    """
    Base exception for all archive errors.
    """


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


if LZMA_CAPABLE:
    def extract_lzma(path, force=False):
        """
        Extracts a XZ compressed file to the same directory.
        """
        extracted_file = os.path.splitext(path)[0]
        if not force and os.path.exists(extracted_file):
            return extracted_file
        with open(path, 'rb') as file_obj:
            with open(extracted_file, 'wb') as newfile_obj:
                newfile_obj.write(lzma.decompress(file_obj.read()))
        return extracted_file


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
        :return: the first member of the archive, a file or directory or None
                 if the archive is empty
        """
        self._engine.extractall(path)
        if self.is_zip:
            self._update_zip_extra_attrs(path)
            files = self._engine.namelist()
            if files:
                return files[0].strip(os.sep)
            else:
                return None

        files = self._engine.getnames()
        if files:
            return files[0]
        return None

    def _update_zip_extra_attrs(self, dst_dir):
        if platform.system() != "Linux":
            LOG.warn("Attr handling in zip files only supported on Linux.")
            return
        # Walk all files and re-create files as symlinks
        for path, info in self._engine.NameToInfo.items():
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
                if not os.path.islink(dst):
                    # Link created as an ordinary file containing the dst path
                    with open(dst, 'r') as dst_path:
                        src = dst_path.read()
                else:
                    # Link is already there and could be outdated. Let's read
                    # the original destination from the zip file.
                    src = self._engine.read(path)
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
    return (zipfile.is_zipfile(filename) or tarfile.is_tarfile(filename) or
            is_gzip_file(filename))


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
    if is_gzip_file(filename) and not tarfile.is_tarfile(filename):
        return gzip_uncompress(filename, path)
    else:
        with ArchiveFile.open(filename) as x:
            return x.extract(path)


# Some aliases
create = compress
extract = uncompress
