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

import bz2
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


# Magic bytes for different archive formats
MAGIC_BYTES = {
    "gzip": {
        "magic": b"\037\213",
        "description": "The first two bytes that all gzip files start with",
    },
    "zstd": {
        "magic": b"\x28\xb5\x2f\xfd",
        "description": "The first bytes that all zstd files start with. See https://datatracker.ietf.org/doc/html/rfc8878#section-3.1.1-3.2",
    },
    "bzip2": {
        "magic": b"BZh",
        "description": "The first three bytes that all bzip2 files start with",
    },
    "xz": {
        "magic": b"\xfd\x37\x7a\x58\x5a\x00",
        "description": "The first six bytes that all xz files start with",
    },
}

#: A valid zstd archive with "avocado\n" as content.  Created with:
#: echo "avocado" | zstd -c
ZSTD_AVOCADO = (
    MAGIC_BYTES["zstd"]["magic"]
    + b"\x04\x58\x41\x00\x00\x61\x76\x6f\x63\x61\x64\x6f\x0a\x3c\xfc\x9f\xb9"
)


def _is_file_with_magic_bytes(path, magic_bytes):
    """
    Checks if file given by path starts with the specified magic bytes

    :param path: Path to the file to check
    :param magic_bytes: The magic bytes to look for at the start of the file
    :return: True if the file starts with the magic bytes, False otherwise
    """
    try:
        with open(path, "rb") as file_obj:
            return file_obj.read(len(magic_bytes)) == magic_bytes
    except (IOError, OSError):
        return False


def is_gzip_file(path):
    """
    Checks if file given by path has contents that suggests gzip file
    """
    return _is_file_with_magic_bytes(path, MAGIC_BYTES["gzip"]["magic"])


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
    # First try with magic bytes
    if _is_file_with_magic_bytes(path, MAGIC_BYTES["xz"]["magic"]):
        return True

    # If that fails, try the more thorough but slower method
    try:
        with lzma.LZMAFile(path, "rb") as lzma_file:
            try:
                _ = lzma_file.read(1)
            except EOFError:
                return False
        return True
    except (IOError, OSError, lzma.LZMAError):
        return False


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
    return _is_file_with_magic_bytes(path, MAGIC_BYTES["zstd"]["magic"])


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
            return None
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


def bzip2_uncompress(path, output_path=None, force=False):
    """
    Extracts a bzip2 compressed file.
    """
    output_path = _decide_on_path(path, ".bz2", output_path)
    if not force and os.path.exists(output_path):
        return output_path
    try:
        with bz2.open(path, "rb") as file_obj:
            with open(output_path, "wb") as newfile_obj:
                shutil.copyfileobj(file_obj, newfile_obj)
    except OSError as e:
        raise ArchiveException(
            f"Unable to decompress {path} into {output_path}: {e}"
        ) from e
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
        # ZIP archives
        ".zip": (True, False, zipfile.ZipFile, ""),
        # TAR archives (uncompressed)
        ".tar": (False, True, tarfile.open, ""),
        # TAR archives with gzip compression
        ".tar.gz": (False, True, tarfile.open, ":gz"),
        ".tgz": (False, True, tarfile.open, ":gz"),
        # TAR archives with bzip2 compression
        ".tar.bz2": (False, True, tarfile.open, ":bz2"),
        ".tbz2": (False, True, tarfile.open, ":bz2"),
        # TAR archives with xz compression
        ".tar.xz": (False, True, tarfile.open, ":xz"),
        ".txz": (False, True, tarfile.open, ":xz"),
        ".xz": (False, True, tarfile.open, ":xz"),
        # TAR archives with zstd compression
        ".tar.zst": (False, True, tarfile.open, ":zstd"),
        ".tzst": (False, True, tarfile.open, ":zstd"),
        # Standalone compressed files (not tar archives)
        ".gz": (False, False, None, "gz"),
        ".bz2": (False, False, None, "bz2"),
        ".zst": (False, False, None, "zst"),
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
        self.is_zip = False
        self.is_tar = False
        self.is_compressed = False
        self.compression_type = None

        # First try to detect by extension
        for ext, value in ArchiveFile._extension_table.items():
            if filename.endswith(ext):
                (self.is_zip, self.is_tar, engine, extra_mode) = value

                # Handle standalone compressed files
                if not self.is_zip and not self.is_tar and engine is None:
                    self.is_compressed = True
                    self.compression_type = extra_mode
                    # For standalone compressed files, we'll use the appropriate
                    # extraction function in the extract method
                    self._engine = None
                    return

                self.mode += extra_mode
                self._engine = engine(self.filename, self.mode)
                return

        # If extension detection fails, try content-based detection
        if mode == "r":  # Only attempt content detection in read mode
            detected = self._detect_archive_type(filename)
            if detected:
                (self.is_zip, self.is_tar, engine, extra_mode) = detected
                self.mode += extra_mode
                self._engine = engine(self.filename, self.mode)
                return

        # If we get here, it's not a recognized archive
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
        # Handle standalone compressed files
        if self.is_compressed:
            if self.compression_type == "gz":
                return gzip_uncompress(self.filename, path)
            if self.compression_type == "bz2":
                return bzip2_uncompress(self.filename, path)
            if self.compression_type == "zst":
                return zstd_uncompress(self.filename, path)
            # Note: bz2 is handled by tarfile, xz by lzma_uncompress (called from top-level uncompress)
            # This check might be slightly redundant now but kept for safety.
            if self.compression_type not in ("gz", "zst"):
                raise ArchiveException(
                    f"Unsupported standalone compression type for direct extraction: {self.compression_type}"
                )

        # Handle regular archives (zip and tar)
        self._engine.extractall(path)
        if self.is_zip:
            self._update_zip_extra_attrs(path)
            files = self._engine.namelist()
            if files:
                return files[0].strip(os.sep)
        else:  # is_tar
            files = self._engine.getnames()
            if files:
                return files[0]
        # If archive is empty (no files)
        return None

    @staticmethod
    def _detect_archive_type(filename):
        """
        Detect archive type based on file content.

        :param filename: the archive file name.
        :return: tuple of (is_zip, is_tar, engine, extra_mode) or None if not an archive.
        """
        result = None
        # Check for ZIP file
        if zipfile.is_zipfile(filename):
            result = (True, False, zipfile.ZipFile, "")
        # Check for TAR file
        elif tarfile.is_tarfile(filename):
            # Detect compression method for tar files
            if _is_file_with_magic_bytes(filename, MAGIC_BYTES["gzip"]["magic"]):
                result = (False, True, tarfile.open, ":gz")
            elif _is_file_with_magic_bytes(filename, MAGIC_BYTES["zstd"]["magic"]):
                result = (False, True, tarfile.open, ":zstd")
            elif _is_file_with_magic_bytes(filename, MAGIC_BYTES["xz"]["magic"]):
                result = (False, True, tarfile.open, ":xz")
            else:  # Regular tar file
                result = (False, True, tarfile.open, "")
        # Check for standalone compressed files
        elif is_gzip_file(filename):
            result = (False, False, None, "gz")
        elif is_zstd_file(filename):
            result = (False, False, None, "zst")
        elif is_bzip2_file(filename):
            result = (False, False, None, "bz2")
        elif is_lzma_file(filename):
            result = (False, False, None, "xz")

        return result

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


def is_bzip2_file(path):
    """
    Checks if file given by path has contents that suggests bzip2 file
    """
    return _is_file_with_magic_bytes(path, MAGIC_BYTES["bzip2"]["magic"])


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
        or is_bzip2_file(filename)
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
    if is_bzip2_file(filename) and not is_tar:
        return bzip2_uncompress(filename, path)

    try:
        with ArchiveFile.open(filename) as x:
            return x.extract(path)
    except ArchiveException as e:
        # If we get here but is_archive() returns True, we have an archive
        # that we can detect but not extract. Provide a more helpful error message.
        if is_archive(filename):
            raise ArchiveException(
                f"File '{filename}' is detected as an archive but its format "
                f"is not supported for extraction: {e}"
            ) from e
        raise


# Some aliases
create = compress
extract = uncompress
