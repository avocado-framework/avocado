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
# Copyright: Red Hat Inc. 2017
# Author: Amador Pahim <apahim@redhat.com>

"""
Provides VM images acquired from official repositories
"""

import os
import tempfile
import uuid

from . import asset
from . import path as utils_path
from . import process

try:
    import lzma
    LZMA_CAPABLE = True
except ImportError:
    LZMA_CAPABLE = False


class VMImageError(Exception):
    """
    Generic error class for VM Image exceptions
    """


class Image(object):

    def __init__(self, name, major, minor, build, arch, checksum, algorithm,
                 cache_dir, url):
        """
        Vm Image representation.

        :param name: Name of the Operating System
        :param major: Major part of the version
        :param minor: Minor part of the version
        :param build: Build identifier
        :param arch: Architecture
        :param checksum: Hash of the image, used to validate the download
        :param algorithm: Algorithm of the provided checksum
        :param url: URL with the filename of the image
        """
        self.name = name
        self.major = major
        self.minor = minor
        self.build = build
        self.arch = arch
        self.checksum = checksum
        self.algorithm = algorithm
        if cache_dir is None:
            cache_dir = tempfile.gettempdir()
        self.cache_dir = cache_dir
        self.url = url
        self.username = None
        self.password = None
        self.path = None
        self.get()

    def get(self):
        """
        Download the image with cache using the Asset Fetcher,
        decompress image if needed and provides a backed image.
        """
        asset_path = asset.Asset(name=self.url,
                                 asset_hash=self.checksum,
                                 algorithm=self.algorithm,
                                 locations=None,
                                 cache_dirs=[self.cache_dir],
                                 expire=None).fetch()

        if os.path.splitext(asset_path)[1] == '.xz':
            if LZMA_CAPABLE:
                asset_path = self._extract(asset_path)
            else:
                raise VMImageError('Cannot uncompress image')

        self.path = self._create_backed_image(asset_path)

    def customize(self, username=None, password=None, install=None,
                  uninstall=None):
        """
        Wrapper around virt-customize to make custom settings in the
        VM disk image.

        :param username: Username to configure
        :param password: Password of the provided user
        :param install: List of packages to install
        :param uninstall: List of packages to uninstall
        :type username: string
        :type password: string
        :type install: list
        :type uninstall: list
        """
        virt_customize = utils_path.find_command('virt-customize')
        if not self.path:
            raise VMImageError('No image available')

        cmd = '%s -a %s' % (virt_customize, self.path)

        if username is not None and password is not None:
            self.username = username
            self.password = password
            cmd += ' --password %s:password:%s' % (username, password)

        if install:
            cmd += ' --install %s' % ','.join(install)

        if uninstall:
            cmd += ' --uninstall %s' % ','.join(uninstall)

        process.run(cmd)

    def remove(self):
        """
        Removes the VM Image
        """
        try:
            os.remove(self.path)
        except:
            pass
        self.path = None

    @staticmethod
    def _create_backed_image(source_image):
        """
        Creates a Qcow2 backed image using the original image
        as backing file.
        """
        qemu_img = utils_path.find_command('qemu-img')
        new_image = '%s-%s' % (source_image, uuid.uuid4())
        cmd = '%s create -f qcow2 -b %s %s' % (qemu_img,
                                               source_image,
                                               new_image)
        process.run(cmd)
        return new_image

    @staticmethod
    def _extract(path, force=False):
        """
        Extracts a XZ compressed file to the same directory.
        """
        extracted_file = os.path.splitext(path)[0]
        if not force and os.path.exists(extracted_file):
            return extracted_file
        with open(path, 'r') as file_obj:
            with open(extracted_file, 'wb') as newfile_obj:
                newfile_obj.write(lzma.decompress(file_obj.read()))
        return extracted_file


class CentOS(Image):
    def __init__(self, name=None, major=None, minor=None, build=None,
                 arch=None, checksum=None, algorithm=None, cache_dir=None):
        """
        CentOS Qcow2 GenericCloud compressed image
        """
        required_args = ['major', 'build', 'arch']
        for arg in required_args:
            if eval(arg) is None:
                raise VMImageError('Required args: %s' % ','.join(required_args))

        url = ('https://cloud.centos.org/'
               'centos/{major}/images/'
               'CentOS-{major}-{arch}-GenericCloud-{build}.qcow2.xz')
        url = url.format(major=major, build=build, arch=arch)

        if name is None:
            name = 'CentOS'

        super(CentOS, self).__init__(name=name,
                                     major=major,
                                     minor=minor,
                                     build=build,
                                     arch=arch,
                                     checksum=checksum,
                                     algorithm=algorithm,
                                     cache_dir=cache_dir,
                                     url=url)


class Fedora(Image):
    def __init__(self, name=None, major=None, minor=None, build=None,
                 arch=None, checksum=None, algorithm=None, cache_dir=None):
        """
        Fedora Qcow2 Cloud Base image
        """
        required_args = ['major', 'minor', 'build', 'arch']
        for arg in required_args:
            if eval(arg) is None:
                raise VMImageError('Required args: %s' % ','.join(required_args))

        url = ('https://download.fedoraproject.org/'
               'pub/fedora/linux/releases/{major}/CloudImages/{arch}/images/'
               'Fedora-Cloud-Base-{major}-{minor}.{build}.{arch}.qcow2')
        url = url.format(major=major, minor=minor, build=build, arch=arch)

        if name is None:
            name = 'Fedora'

        super(Fedora, self).__init__(name=name,
                                     major=major,
                                     minor=minor,
                                     build=build,
                                     arch=arch,
                                     checksum=checksum,
                                     algorithm=algorithm,
                                     cache_dir=cache_dir,
                                     url=url)


class Ubuntu(Image):
    def __init__(self, name=None, major=None, minor=None, build=None,
                 arch=None, checksum=None, algorithm=None, cache_dir=None):
        """
        Ubuntu Qcow2 Server Cloud image
        """
        required_args = ['major', 'minor', 'arch']
        for arg in required_args:
            if eval(arg) is None:
                raise VMImageError('Required args: %s' % ','.join(required_args))

        url = ('https://cloud-images.ubuntu.com/'
               'releases/{major}.{minor}/release/'
               'ubuntu-{major}.{minor}-server-cloudimg-{arch}.img')
        url = url.format(major=major, minor=minor, arch=arch)

        if name is None:
            name = 'Ubuntu'

        super(Ubuntu, self).__init__(name=name,
                                     major=major,
                                     minor=minor,
                                     build=build,
                                     arch=arch,
                                     checksum=checksum,
                                     algorithm=algorithm,
                                     cache_dir=cache_dir,
                                     url=url)
