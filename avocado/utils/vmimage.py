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


class ImageProviderBase(object):
    """
    Base class to define the common methods and attributes of an
    image. Intended to be sub-classed by the specific image providers.
    """

    def __init__(self, version, build, arch):

        self.url_versions = None
        self.url_images = None
        self.image_pattern = None

        self._version = version
        self._best_version = None
        self.build = build
        self.arch = arch

    @property
    def version(self):
        return self._best_version or self.get_version()

    def get_version(self):
        """
        Probes the higher version available for the current parameters.
        """
        pattern = '^%s/$' % self._version
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
                        # So it's just a string
                        resulting_versions.append(version)
            self._best_version = max(resulting_versions)
            return self._best_version
        else:
            raise ImageProviderError('Version not available at %s' %
                                     self.url_versions)

    def get_image_url(self):
        """
        Probes the higher image available for the current parameters.
        """
        url_images = self.url_images.format(version=self.version,
                                            build=self.build,
                                            arch=self.arch)
        image = self.image_pattern.format(version=self.version,
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
            raise ImageProviderError("No images matching '%s' at '%s'. "
                                     "Wrong arch?" % (image, url_images))


class FedoraImageProvider(ImageProviderBase):
    """
    Fedora Image Provider
    """

    name = 'Fedora'

    def __init__(self, version='[0-9]+', build='[0-9]+.[0-9]+',
                 arch=os.uname()[4]):
        super(FedoraImageProvider, self).__init__(version, build, arch)
        self.url_versions = 'https://dl.fedoraproject.org/pub/fedora/linux/releases/'
        self.url_images = self.url_versions + '{version}/CloudImages/{arch}/images/'
        self.image_pattern = 'Fedora-Cloud-Base-{version}-{build}.{arch}.qcow2$'


class FedoraSecondaryImageProvider(ImageProviderBase):
    """
    Fedora Secondary Image Provider
    """

    name = 'FedoraSecondary'

    def __init__(self, version='[0-9]+', build='[0-9]+.[0-9]+',
                 arch=os.uname()[4]):
        super(FedoraSecondaryImageProvider, self).__init__(version, build,
                                                           arch)
        self.url_versions = 'https://dl.fedoraproject.org/pub/fedora-secondary/releases/'
        self.url_images = self.url_versions + '{version}/CloudImages/{arch}/images/'
        self.image_pattern = 'Fedora-Cloud-Base-{version}-{build}.{arch}.qcow2$'


class CentOSImageProvider(ImageProviderBase):
    """
    CentOS Image Provider
    """

    name = 'CentOS'

    def __init__(self, version='[0-9]+', build='[0-9]{4}', arch=os.uname()[4]):
        super(CentOSImageProvider, self).__init__(version, build, arch)
        self.url_versions = 'https://cloud.centos.org/centos/'
        self.url_images = self.url_versions + '{version}/images/'
        if LZMA_CAPABLE:
            self.image_pattern = 'CentOS-{version}-{arch}-GenericCloud-{build}.qcow2.xz$'
        else:
            self.image_pattern = 'CentOS-{version}-{arch}-GenericCloud-{build}.qcow2$'


class UbuntuImageProvider(ImageProviderBase):
    """
    Ubuntu Image Provider
    """

    name = 'Ubuntu'

    def __init__(self, version='[0-9]+.[0-9]+', build=None,
                 arch=os.uname()[4]):
        # Ubuntu uses 'amd64' instead of 'x86_64'
        if arch == 'x86_64':
            arch = 'amd64'

        super(UbuntuImageProvider, self).__init__(version, build, arch)
        self.url_versions = 'http://cloud-images.ubuntu.com/releases/'
        self.url_images = self.url_versions + 'releases/{version}/release/'
        self.image_pattern = 'ubuntu-{version}-server-cloudimg-{arch}.img'


class DebianImageProvider(ImageProviderBase):
    """
    Debian Image Provider
    """

    name = 'Debian'

    def __init__(self, version='[0-9]+.[0-9]+.[0-9]+-.*', build=None,
                 arch=os.uname()[4]):
        # Debian uses 'amd64' instead of 'x86_64'
        if arch == 'x86_64':
            arch = 'amd64'

        super(DebianImageProvider, self).__init__(version, build, arch)
        self.url_versions = 'https://cdimage.debian.org/cdimage/openstack/'
        self.url_images = self.url_versions + '{version}/'
        self.image_pattern = 'debian-{version}-openstack-{arch}.qcow2$'


class Image(object):
    def __init__(self, name, url, version, arch, checksum, algorithm,
                 cache_dir):
        self.name = name
        self.url = url
        self.version = version
        self.arch = arch
        self.checksum = checksum
        self.algorithm = algorithm
        self.cache_dir = cache_dir

        self._path = None
        self._base_image = None
        self.get()

    @property
    def path(self):
        return self._path or self.get()

    @property
    def base_image(self):
        return self._base_image

    def __repr__(self):
        return "<%s name=%s version=%s arch=%s>" % (self.__class__.__name__,
                                                    self.name,
                                                    self.version,
                                                    self.arch)

    def get(self):
        asset_path = asset.Asset(name=self.url,
                                 asset_hash=self.checksum,
                                 algorithm=self.algorithm,
                                 locations=None,
                                 cache_dirs=[self.cache_dir],
                                 expire=None).fetch()

        if os.path.splitext(asset_path)[1] == '.xz':
            asset_path = self._extract(asset_path)

        self._base_image = asset_path
        self._path = self._take_snapshot()
        return self._path

    def _take_snapshot(self):
        """
        Takes a snapshot from the current image.
        """
        qemu_img = utils_path.find_command('qemu-img')
        name, extension = os.path.splitext(self.base_image)
        new_image = '%s-%s%s' % (name, str(uuid.uuid4()).split('-')[0],
                                 extension)
        cmd = '%s create -f qcow2 -b %s %s' % (qemu_img,
                                               self.base_image,
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


def get(name=None, version=None, build=None, arch=None, checksum=None,
        algorithm=None, cache_dir=None):
    """
    Wrapper to get the best Image Provider, according to the parameters
    provided.

    :param name: (optional) Name of the Image Provider, usually matches
                 the distro name.
    :param version: (optional) Version of the system image.
    :param build: (optional) Build number of the system image.
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

    if name is not None:
        name = name.lower()

    if cache_dir is None:
        cache_dir = tempfile.gettempdir()

    providers_list = list_providers()
    provider_args = {}
    if version is not None:
        provider_args['version'] = version
    if build is not None:
        provider_args['build'] = version
    if arch is not None:
        provider_args['arch'] = arch

    for provider in providers_list:
        if name is None or name == provider.name.lower():
            cls = provider(**provider_args)
            try:
                return Image(name=cls.name,
                             url=cls.get_image_url(),
                             version=cls.version,
                             arch=cls.arch,
                             checksum=checksum,
                             algorithm=algorithm,
                             cache_dir=cache_dir)
            except ImageProviderError:
                pass

    raise AttributeError('Provider not available')


def list_providers():
    """
    List the available Image Providers
    """
    return [_ for _ in globals().itervalues()
            if (_ != ImageProviderBase and
                isinstance(_, type) and
                issubclass(_, ImageProviderBase))]
