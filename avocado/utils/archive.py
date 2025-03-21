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
import lzma
import os
import platform
import shutil
import stat
import subprocess
import tarfile
import zipfile

LOG = logging.getLogger(__name__)


#: The first two bytes that all gzip files start with
GZIP_MAGIC = b"\037\213"

#: The first two bytes that all zstd files start with.  See
#: https://datatracker.ietf.org/doc/html/rfc8878#section-3.1.1-3.2
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"

#: A valid zstd archive with "avocado\n" as content.  Created with:
#: echo "avocado" | zstd -c
ZSTD_AVOCADO = (
    ZSTD_MAGIC + b"\x04\x58\x41\x00\x00\x61\x76\x6f\x63\x61\x64\x6f\x0a\x3c\xfc\x9f\xb9"
)


def is_gzip_file(path):
    """
    Checks if file given by path has contents that suggests gzip file
    """
    with open(path, "rb") as gzip_file:  # pylint: disable=W1514
        return gzip_file.read(len(GZIP_MAGIC)) == GZIP_MAGIC


def gzip_uncompress(path, output_path):
    """
    Uncompress a gzipped file at path, to either a file or dir at output_path
    """
    with gzip.GzipFile(filename=path, mode="rb") as input_file:
        if os.path.isdir(output_path):
            basename = os.path.basename(path)
            if basename.endswith(".gz"):
                basename = basename[:-3]
            output_path = os.path.join(output_path, basename)
        with open(output_path, "wb") as output_file:
            while True:
                chunk = input_file.read(4096)
                if not chunk:
                    break
                output_file.write(chunk)
        return output_path


def is_lzma_file(path):
    """
    Checks if file given by path has contents that suggests lzma file
    """
    with lzma.LZMAFile(path, "rb") as lzma_file:
        try:
            _ = lzma_file.read(1)
        except lzma.LZMAError:
            return False
        except EOFError:
            return False
    return True


def _decide_on_path(path, suffix, output_path=None):
    if output_path is None:
        output_path = os.path.splitext(path)[0]
    elif os.path.isdir(output_path):
        basename = os.path.basename(path)
        if basename.endswith(suffix):
            basename = os.path.splitext(basename)[0]
        output_path = os.path.join(output_path, basename)
    return output_path


def lzma_uncompress(path, output_path=None, force=False):
    """
    Extracts a XZ compressed file to the same directory.
    """
    output_path = _decide_on_path(path, ".xz", output_path)
    if not force and os.path.exists(output_path):
        return output_path
    with lzma.open(path, "rb") as file_obj:
        with open(output_path, "wb") as newfile_obj:
            newfile_obj.write(file_obj.read())
    return output_path


def is_zstd_file(path):
    """
    Checks if file given by path has contents that suggests zstd file
    """
    with open(path, "rb") as zstd_file:  # pylint: disable=W1514
        return zstd_file.read(len(ZSTD_MAGIC)) == ZSTD_MAGIC


def probe_zstd_cmd():
    """
    Attempts to find a suitable zstd tool that behaves as expected

    :rtype: str or None
    :returns: path to a suitable zstd executable or None if not found
    """
    zstd_cmd = shutil.which("zstd")
    if zstd_cmd is not None:
        proc = subprocess.run(
            [zstd_cmd, "-d"],
            input=ZSTD_AVOCADO,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode or proc.stdout != b"avocado\n":
            LOG.error("zstd command does not seem to be the Zstandard compression tool")
        return zstd_cmd
    return None


def zstd_uncompress(path, output_path=None, force=False):
    """
    Extracts a zstd compressed file.
    """
    zstd_cmd = probe_zstd_cmd()
    if not zstd_cmd:
        raise ArchiveException("Unable to find a suitable zstd compression tool")
    output_path = _decide_on_path(path, ".zst", output_path)
    if not force and os.path.exists(output_path):
        return output_path
    proc = subprocess.run(
        [zstd_cmd, "-d", path, "-o", output_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode:
        raise ArchiveException(
            f"Unable to decompress {path} into {output_path}: {proc.stderr}"
        )
    return output_path


class ArchiveException(Exception):
    """
    Base exception for all archive errors.
    """


class ArchiveFile:
    """
    Class that represents an Archive file.

    Archives are ZIP files or Tarballs.
    """

    # extension info: is_zip, is_tar, zipfile|tarfile, +mode
    _extension_table = {
        ".zip": (True, False, zipfile.ZipFile, ""),
        ".tar": (False, True, tarfile.open, ""),
        ".tar.gz": (False, True, tarfile.open, ":gz"),
        ".tgz": (False, True, tarfile.open, ":gz"),
        ".tar.bz2": (False, True, tarfile.open, ":bz2"),
        ".tbz2": (False, True, tarfile.open, ":bz2"),
        ".xz": (False, True, tarfile.open, ":xz"),
    }

    def __init__(self, filename, mode="r"):
        """
        Creates an instance of :class:`ArchiveFile`.

        :param filename: the archive file name.
        :param mode: file mode, `r` read, `w` write.
        """
        self.filename = filename
        self.mode = mode
        engine = None
        for ext, value in ArchiveFile._extension_table.items():
            if filename.endswith(ext):
                (self.is_zip, self.is_tar, engine, extra_mode) = value
        if engine is not None:
            self.mode += extra_mode
            self._engine = engine(self.filename, self.mode)
        else:
            raise ArchiveException("file is not an archive")

    def __repr__(self):
        return f"ArchiveFile('{self.filename}', '{self.mode}')"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self._engine is not None:
            self.close()

    @classmethod
    def open(cls, filename, mode="r"):
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

    def extract(self, path="."):
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
            return None

        files = self._engine.getnames()
        if files:
            return files[0]
        return None

    def _update_zip_extra_attrs(self, dst_dir):
        if platform.system() != "Linux":
            LOG.warning("Attr handling in zip files only supported on Linux.")
            return
        # Walk all files and re-create files as symlinks
        for path, info in self._engine.NameToInfo.items():
            dst = os.path.join(dst_dir, path)
            if not os.path.exists(dst):
                LOG.warning(
                    "One or more files in the ZIP archive '%s' could "
                    "not be found after extraction. Their paths are "
                    "probably stored in unsupported format and their "
                    "attributes are not going to be updated",
                    self.filename,
                )
                return
            attr = info.external_attr >> 16
            if attr & stat.S_IFLNK == stat.S_IFLNK:
                if not os.path.islink(dst):
                    # Link created as an ordinary file containing the dst path
                    with open(dst, "r") as dst_path:  # pylint: disable=W1514
                        src = dst_path.read()
                else:
                    # Link is already there and could be outdated. Let's read
                    # the original destination from the zip file.
                    src = self._engine.read(path)
                try:
                    os.remove(dst)
                    os.symlink(src, dst)
                except (OSError, FileNotFoundError) as e:
                    LOG.warning("Failed to update symlink '%s': %s", dst, e)
                    continue
                continue  # Don't override any other attributes on links
            mode = attr & 511  # Mask only permissions
            if mode and mode != 436:  # If mode is stored and is not default
                try:
                    os.chmod(dst, mode)
                except (OSError, FileNotFoundError) as e:
                    LOG.warning("Failed to update permissions for '%s'", e)

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
    return (
        zipfile.is_zipfile(filename)
        or tarfile.is_tarfile(filename)
        or is_gzip_file(filename)
        or is_lzma_file(filename)
        or is_zstd_file(filename)
    )


def compress(filename, path):
    """
    Compress files in an archive.

    :param filename: archive file name.
    :param path: origin directory path to files to compress. No
                 individual files allowed.
    """
    with ArchiveFile.open(filename, "w") as x:
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for name in files:
                    newroot = root.replace(path, "")
                    x.add(os.path.join(root, name), os.path.join(newroot, name))
        elif os.path.isfile(path):
            x.add(path, os.path.basename(path))


def uncompress(filename, path):
    """
    Extract files from an archive.

    :param filename: archive file name.
    :param path: destination path to extract to.
    """
    is_tar = tarfile.is_tarfile(filename)
    if is_gzip_file(filename) and not is_tar:
        return gzip_uncompress(filename, path)
    if is_lzma_file(filename) and not is_tar:
        return lzma_uncompress(filename, path)
    if is_zstd_file(filename) and not is_tar:
        return zstd_uncompress(filename, path)
    with ArchiveFile.open(filename) as x:
        return x.extract(path)


# Some aliases
create = compress
extract = uncompress
