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

import hashlib
import os
import re
import tempfile
import urllib2
import uuid

try:
    import lzma
    LZMA_CAPABLE = True
except ImportError:
    LZMA_CAPABLE = False

from HTMLParser import HTMLParser

from . import asset
from . import path as utils_path
from . import process


class ImageProviderError(Exception):
    """
    Generic error class for ImageProvider
    """


class VMImageHtmlParser(HTMLParser):
    """
    Custom HTML parser to extract the href items that match
    a given pattern
    """

    def __init__(self, pattern):
        HTMLParser.__init__(self)
        self.items = []
        self.pattern = pattern

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        for attr in attrs:
            if attr[0] == 'href' and re.match(self.pattern, attr[1]):
                self.items.append(attr[1].strip('/'))


class ImageBase(object):
    """
    Base class to define the common methods and attributes of an
    image. Intended to be sub-classed by the specific image providers.
    """

    def __init__(self, version, build, arch, checksum, algorithm, cache_dir):
        self.version = version
        self.build = build
        self.arch = arch
        self.checksum = checksum
        self.algorithm = algorithm
        self.cache_dir = cache_dir

        self.url_versions = None
        self.url_images = None
        self.image_pattern = None

        self._fingerprint = None
        self._path = None
        self._snapshot = None
        self._backing_file = None
        self._url = None

    @property
    def path(self):
        """
        Returns the image path on local system. Any changes in
        parameters will make the path to be updated to reflect the new
        parameters.
        """
        if self._fingerprint == self._get_fingerprint():
            return self._path or self._update_path()
        return self._update_path()

    @property
    def snapshot(self):
        """
        Returns the snapshot image of the current image path. Any
        changes in the current image path will make the snapshot to be
        taken again.
        """
        if self._backing_file == self.path:
            return self._snapshot or self._take_snapshot()
        return self._take_snapshot()

    def _get_fingerprint(self):
        """
        Method to track changes in the parameters.
        """
        fingerprint = []
        for item in self.__dict__:
            if not item.startswith('_'):
                fingerprint.append(self.__dict__[item])
        return hashlib.sha1(str(fingerprint)).hexdigest()

    def _update_path(self):
        """
        Acquires the image, updating the path.
        """
        self._fingerprint = self._get_fingerprint()
        self._url = self._get_url()
        asset_path = asset.Asset(name=self._url,
                                 asset_hash=self.checksum,
                                 algorithm=self.algorithm,
                                 locations=None,
                                 cache_dirs=[self.cache_dir],
                                 expire=None).fetch()

        if os.path.splitext(asset_path)[1] == '.xz':
            asset_path = self._extract(asset_path)

        self._path = asset_path
        return self._path

    def _take_snapshot(self):
        """
        Takes a snapshot from the current image.
        """
        self._backing_file = self.path
        qemu_img = utils_path.find_command('qemu-img')
        name, extension = os.path.splitext(self._backing_file)
        new_image = '%s-%s%s' % (name, str(uuid.uuid4()).split('-')[0],
                                 extension)
        cmd = '%s create -f qcow2 -b %s %s' % (qemu_img,
                                               self._backing_file,
                                               new_image)
        process.run(cmd)
        self._snapshot = new_image
        return self._snapshot

    def _get_url(self):
        """
        Probes the full image URL for the current parameters.
        """
        version = self._get_version()
        return self._get_image(version)

    def _get_version(self):
        """
        Probes the higher version available for the current parameters.
        """
        pattern = '^%s/$' % self.version

        parser = VMImageHtmlParser(pattern)
        try:
            parser.feed(urllib2.urlopen(self.url_versions).read())
        except urllib2.HTTPError:
            raise ImageProviderError('Cannot open %s' % self.url_versions)
        if parser.items:
            resulting_versions = []
            for version in parser.items:
                # Trying to convert version to int or float so max()
                # can compare numerical values.
                try:
                    # Can it be converted to integer?
                    resulting_versions.append(int(version))
                except ValueError:
                    try:
                        # Can it be converted to float?
                        resulting_versions.append(float(version))
                    except ValueError:
                        # So it's juat a string
                        resulting_versions.append(version)
            return max(resulting_versions)
        else:
            raise ImageProviderError('Version not available at %s' %
                                     self.url_versions)

    def _get_image(self, version):
        """
        Probes the higher image available for the current parameters.
        """
        url_images = self.url_images.format(version=version,
                                            build=self.build,
                                            arch=self.arch)
        image = self.image_pattern.format(version=version,
                                          build=self.build,
                                          arch=self.arch)
        parser = VMImageHtmlParser(image)
        try:
            content = urllib2.urlopen(url_images).read()
            parser.feed(content)
        except urllib2.HTTPError:
            raise ImageProviderError('Cannot open %s' % url_images)

        if parser.items:
            return url_images + max(parser.items)
        else:
            raise ImageProviderError("No images matching '%s' at '%s'" %
                                     (image, url_images))

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


class FedoraImageProvider(ImageBase):
    """
    Fedora Image Provider
    """

    name = 'Fedora'

    def __init__(self, version='[0-9]+', build='[0-9]+.[0-9]+',
                 arch=os.uname()[4], checksum=None, algorithm=None,
                 cache_dir=tempfile.gettempdir()):

        super(FedoraImageProvider, self).__init__(version, build, arch,
                                                  checksum, algorithm,
                                                  cache_dir)

        # Here you can use string formatting tags corresponding to the
        # arguments accepted (version, build, ...).
        self.url_versions = 'https://dl.fedoraproject.org/pub/fedora/linux/releases/'
        self.url_images = self.url_versions + '{version}/CloudImages/{arch}/images/'
        self.image_pattern = 'Fedora-Cloud-Base-{version}-{build}.{arch}.qcow2$'


class FedoraSecondaryImageProvider(ImageBase):
    """
    Fedora Secondary Image Provider
    """

    name = 'FedoraSecondary'

    def __init__(self, version='[0-9]+', build='[0-9]+.[0-9]+',
                 arch=os.uname()[4], checksum=None, algorithm=None,
                 cache_dir=tempfile.gettempdir()):

        super(FedoraSecondaryImageProvider, self).__init__(version, build,
                                                           arch, checksum,
                                                           algorithm,
                                                           cache_dir)

        # Here you can use string formatting tags corresponding to the
        # arguments accepted (version, build and arch).
        self.url_versions = 'https://dl.fedoraproject.org/pub/fedora-secondary/releases/'
        self.url_images = self.url_versions + '{version}/CloudImages/{arch}/images/'
        self.image_pattern = 'Fedora-Cloud-Base-{version}-{build}.{arch}.qcow2$'


class CentOSImageProvider(ImageBase):
    """
    CentOS Image Provider
    """

    name = 'CentOS'

    def __init__(self, version='[0-9]+', build='[0-9]{4}',
                 arch=os.uname()[4], checksum=None, algorithm=None,
                 cache_dir=tempfile.gettempdir()):

        super(CentOSImageProvider, self).__init__(version, build, arch,
                                                  checksum, algorithm,
                                                  cache_dir)

        # Here you can use string formatting tags corresponding to the
        # arguments accepted (version, build and arch).
        self.url_versions = 'https://cloud.centos.org/centos/'
        self.url_images = self.url_versions + '{version}/images/'
        if LZMA_CAPABLE:
            self.image_pattern = 'CentOS-{version}-{arch}-GenericCloud-{build}.qcow2.xz$'
        else:
            self.image_pattern = 'CentOS-{version}-{arch}-GenericCloud-{build}.qcow2$'


class UbuntuImageProvider(ImageBase):
    """
    Ubuntu Image Provider
    """

    name = 'Ubuntu'

    def __init__(self, version='[0-9]+.[0-9]+', build=None,
                 arch=os.uname()[4], checksum=None, algorithm=None,
                 cache_dir=tempfile.gettempdir()):

        super(UbuntuImageProvider, self).__init__(version, build, arch,
                                                  checksum, algorithm,
                                                  cache_dir)

        # Here you can use string formatting tags corresponding to the
        # arguments accepted (version, build and arch).
        self.url_versions = 'http://cloud-images.ubuntu.com/releases/'
        self.url_images = self.url_versions + 'releases/{version}/release/'
        self.image_pattern = 'ubuntu-{version}-server-cloudimg-{arch}.img'


class DebianImageProvider(ImageBase):
    """
    Debian Image Provider
    """

    name = 'Debian'

    def __init__(self, version='[0-9]+.[0-9]+.[0-9]+-.*', build=None,
                 arch=os.uname()[4], checksum=None, algorithm=None,
                 cache_dir=tempfile.gettempdir()):

        super(DebianImageProvider, self).__init__(version, build, arch,
                                                  checksum, algorithm,
                                                  cache_dir)

        # Here you can use string formatting tags corresponding to the
        # arguments accepted (version, build and arch).
        self.url_versions = 'https://cdimage.debian.org/cdimage/openstack/'
        self.url_images = self.url_versions + '/{version}/'
        self.image_pattern = 'debian-{version}-openstack-{arch}.qcow2$'


def get(name=None, version=None, build=None, arch=None, checksum=None,
        algorithm=None, cache_dir=None):
    """
    Wrapper to get the best Image Provider, according to the parameters
    provided.

    :param name: (optional) Name of the Image Provider, usually matches
                 the distro name.
    :param version: (optional) Version of the system image.
    :param build: (optional) Build version of the system image.
    :param arch: (optional) Architecture of the system image.
    :param checksum: (optional) Hash of the system image to match after
                     download.
    :param algorithm: (optional) Hash type, used when the checksum is
                      provided.
    :param cache_dir: (optional) Local system path where the images and
                      the snapshots will be held.

    :returns: Image Provider instance that can provide the image
              according to the parameters.
    """

    providers_list = list_providers()

    args = {}
    if version is not None:
        args['version'] = version
    if build is not None:
        args['build'] = build
    if arch is not None:
        args['arch'] = arch
    if checksum is not None:
        args['checksum'] = checksum
    if algorithm is not None:
        args['algorithm'] = algorithm
    if cache_dir is not None:
        args['cache_dir'] = cache_dir

    if name is None:
        for provider in providers_list:
            cls = provider(**args)
            try:
                cls.path
                return cls
            except ImageProviderError:
                pass

    _name = name.lower()
    for provider in providers_list:
        if _name == provider.name.lower():
            return provider(**args)

    raise AttributeError('Provider not available')


def list_providers():
    """
    List the available Image Providers
    """
    return [_ for _ in globals().itervalues()
            if (_ != ImageBase and
                isinstance(_, type) and
                issubclass(_, ImageBase))]
