# license: MIT
#
# Based on django.utils.archive, which is on its turn Based on "python-archive"
# http://pypi.python.org/pypi/python-archive/
#
# Copyright (c) 2010 Gary Wilson Jr. <gary.wilson@gmail.com> and contributors.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Library used to transparently uncompress compressed files.
"""
import logging
import os
import shutil
import tarfile
import zipfile

log = logging.getLogger('avocado.test')


class ArchiveException(Exception):

    """
    Base exception class for all archive errors.
    """
    pass


class UnrecognizedArchiveFormat(ArchiveException):

    """
    Error raised when passed file is not a recognized archive format.
    """
    pass


def extract(path, to_path=''):
    """
    Unpack the tar or zip file at the specified path to the directory
    specified by to_path.
    """
    with Archive(path) as archive:
        archive.extract(to_path)


class Archive(object):

    """
    The external API class that encapsulates an archive implementation.
    """

    def __init__(self, path):
        self._archive = self._archive_cls(path)(path)

    @staticmethod
    def _archive_cls(path):
        cls = None
        if isinstance(path, basestring):
            filename = path
        else:
            try:
                filename = path.name
            except AttributeError:
                raise UnrecognizedArchiveFormat(
                    "File object not a recognized archive format.")
        base, tail_ext = os.path.splitext(filename.lower())
        cls = extension_map.get(tail_ext)
        if not cls:
            base, ext = os.path.splitext(base)
            cls = extension_map.get(ext)
        if not cls:
            raise UnrecognizedArchiveFormat(
                "Path not a recognized archive format: %s" % filename)
        return cls

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def extract(self, to_path=''):
        self._archive.extract(to_path)

    def list(self):
        self._archive.list()

    def close(self):
        self._archive.close()


class BaseArchive(object):

    """
    Base Archive class.  Implementations should inherit this class.
    """

    def split_leading_dir(self, path):
        path = str(path)
        path = path.lstrip('/').lstrip('\\')
        if '/' in path and (('\\' in path and path.find('/') < path.find('\\'))
                            or '\\' not in path):
            return path.split('/', 1)
        elif '\\' in path:
            return path.split('\\', 1)
        else:
            return path, ''

    def has_leading_dir(self, paths):
        """
        Returns true if all the paths have the same leading path name
        (i.e., everything is in one subdirectory in an archive)
        """
        common_prefix = None
        for path in paths:
            prefix, _ = self.split_leading_dir(path)
            if not prefix:
                return False
            elif common_prefix is None:
                common_prefix = prefix
            elif prefix != common_prefix:
                return False
        return True

    def extract(self):
        raise NotImplementedError('Subclasses of BaseArchive must provide an '
                                  'extract() method')

    def list(self):
        raise NotImplementedError('Subclasses of BaseArchive must provide a '
                                  'list() method')


class TarArchive(BaseArchive):

    def __init__(self, path):
        self._archive = tarfile.open(path)

    def list(self, *args, **kwargs):
        self._archive.list(*args, **kwargs)

    def extract(self, to_path):
        # note: python<=2.5 doesn't seem to know about pax headers, filter them
        members = [member for member in self._archive.getmembers()
                   if member.name != 'pax_global_header']
        leading = self.has_leading_dir(members)
        for member in members:
            name = member.name
            if leading:
                name = self.split_leading_dir(name)[1]
            filename = os.path.join(to_path, name)
            if member.isdir():
                if filename and not os.path.exists(filename):
                    os.makedirs(filename)
            else:
                try:
                    extracted = self._archive.extractfile(member)
                except (KeyError, AttributeError) as exc:
                    # Some corrupt tar files seem to produce this
                    # (specifically bad symlinks)
                    log.error("In the tar file %s the member %s is "
                              "invalid: %s" % (name, member.name, exc))
                else:
                    dirname = os.path.dirname(filename)
                    if dirname and not os.path.exists(dirname):
                        os.makedirs(dirname)
                    with open(filename, 'wb') as outfile:
                        if extracted is not None:
                            shutil.copyfileobj(extracted, outfile)
                        else:
                            log.error("Member correspondent to file %s does "
                                      "not seem to be a regular file or a link",
                                      filename)
                finally:
                    if extracted:
                        extracted.close()

    def close(self):
        self._archive.close()


class ZipArchive(BaseArchive):

    def __init__(self, path):
        self._archive = zipfile.ZipFile(path)

    def list(self, *args, **kwargs):
        self._archive.printdir(*args, **kwargs)

    def extract(self, to_path):
        namelist = self._archive.namelist()
        leading = self.has_leading_dir(namelist)
        for name in namelist:
            data = self._archive.read(name)
            if leading:
                name = self.split_leading_dir(name)[1]
            filename = os.path.join(to_path, name)
            dirname = os.path.dirname(filename)
            if dirname and not os.path.exists(dirname):
                os.makedirs(dirname)
            if filename.endswith(('/', '\\')):
                # A directory
                if not os.path.exists(filename):
                    os.makedirs(filename)
            else:
                with open(filename, 'wb') as outfile:
                    outfile.write(data)

    def close(self):
        self._archive.close()

extension_map = {
    '.tar': TarArchive,
    '.tar.bz2': TarArchive,
    '.tar.gz': TarArchive,
    '.tgz': TarArchive,
    '.tz2': TarArchive,
    '.zip': ZipArchive,
}

# Handy functions for ZIP files


def create_zip(name, path):
    """
    Create a ZIP archive from a directory.

    :param name: the name of the zip file. The .zip suffix is optional.
    :param path: the directory with files to compress.
    """
    if name.endswith('.zip') is False:
        name += '.zip'
    with zipfile.ZipFile(name, 'w') as zf:
        for root, dirs, files in os.walk(path):
            for f in files:
                newroot = root.replace(path, '')
                zf.write(os.path.join(root, f),
                         os.path.join(newroot, f), zipfile.ZIP_DEFLATED)


def uncompress_zip(name, path):
    """
    Uncompress a ZIP archive under a directory.

    :param name: the name of the zip file. The .zip suffix is optional.
    :param path: the directory to uncompress de files.
    """
    with zipfile.ZipFile(name) as zf:
        zf.extractall(path)
