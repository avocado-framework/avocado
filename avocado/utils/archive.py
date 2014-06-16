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

import os
import zipfile
import tarfile


class ArchiveException(Exception):

    """
    Base exception for all archive errors.
    """
    pass


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
        '.tar.bz2': (False, True, tarfile.open, ':bz2'), }

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
    :param path: origin path to files to compress.
    """
    with ArchiveFile.open(filename, 'w') as x:
        for root, _, files in os.walk(path):
            for name in files:
                newroot = root.replace(path, '')
                x.add(os.path.join(root, name),
                      os.path.join(newroot, name))


def uncompress(filename, path):
    """
    Extract files from an archive.

    :param filename: archive file name.
    :param path: destination path to extract to.
    """
    with ArchiveFile.open(filename) as x:
        x.extract(path)

# Some aliases
open = ArchiveFile.open
create = compress
extract = uncompress


if __name__ == '__main__':
    import sys
    for arg in sys.argv[1:]:
        try:
            with ArchiveFile.open(arg) as x:
                x.list()
        except ArchiveException:
            print "Skipping '%s': file is not an archive" % arg
