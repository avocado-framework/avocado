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
import uuid
import warnings
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.request import urlopen

from avocado.utils import archive, asset, astring
from avocado.utils import path as utils_path
from avocado.utils import process

# pylint: disable=C0401
#: The "qemu-img" binary used when creating the snapshot images.  If
#: set to None (the default), it will attempt to find a suitable binary
#: with :func:`avocado.utils.path.find_command`, which uses the the
#: system's PATH environment variable
QEMU_IMG = None


#: Default image architecture, which defaults to the current machine
#: architecture, if that's can be retrieved via :func:`os.uname`. If
#: not, it defaults to "x86_64" simply because it's the most commonly
#: used architecture and lack of a better default
if hasattr(os, 'uname'):
    DEFAULT_ARCH = os.uname()[4]
else:
    DEFAULT_ARCH = 'x86_64'


class ImageProviderError(Exception):
    """
    Generic error class for ImageProvider
    """


class VMImageHtmlParser(HTMLParser):  # pylint: disable=W0223
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
                match = attr[1].strip('/')
                if match not in self.items:
                    self.items.append(match)


class ImageProviderBase:
    """
    Base class to define the common methods and attributes of an
    image. Intended to be sub-classed by the specific image providers.
    """

    HTML_ENCODING = 'utf-8'

    def __init__(self, version, build, arch):

        self.url_versions = None
        self.url_images = None
        self.image_pattern = None
        self._file_name = None
        self._version = version
        self._best_version = None
        self.build = build
        self.arch = arch

    @property
    def version(self):
        return self._best_version or self.get_version()

    @property
    def version_pattern(self):
        return '^%s/$' % self._version

    @property
    def file_name(self):
        if self._file_name is None:
            self._file_name = self.image_pattern.format(version=self.version,
                                                        build=self.build,
                                                        arch=self.arch)
        return self._file_name

    def _feed_html_parser(self, url, parser):
        try:
            data = urlopen(url).read()
            parser.feed(astring.to_text(data, self.HTML_ENCODING))
        except HTTPError:
            raise ImageProviderError('Cannot open %s' % self.url_versions)

    @staticmethod
    def get_best_version(versions):
        return max(versions)

    def get_versions(self):
        """Return all available versions for the current parameters."""
        parser = VMImageHtmlParser(self.version_pattern)
        self._feed_html_parser(self.url_versions, parser)

        resulting_versions = []
        if parser.items:
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

        return resulting_versions

    def get_version(self):
        """Probes the higher version available for the current parameters."""
        resulting_versions = self.get_versions()
        if resulting_versions:
            self._best_version = self.get_best_version(resulting_versions)
            return self._best_version
        else:
            raise ImageProviderError('Version not available at %s' %
                                     self.url_versions)

    def get_image_url(self):
        """
        Probes the higher image available for the current parameters.
        """
        if not self.url_images or not self.image_pattern:
            raise ImageProviderError(
                "url_images and image_pattern attributes are required to get image url")

        url_images = self.url_images.format(version=self.version,
                                            build=self.build,
                                            arch=self.arch)
        image = self.image_pattern.format(version=self.version,
                                          build=self.build,
                                          arch=self.arch)
        parser = VMImageHtmlParser(image)

        self._feed_html_parser(url_images, parser)

        if parser.items:
            return url_images + max(parser.items)
        else:
            raise ImageProviderError("No images matching '%s' at '%s'. "
                                     "Wrong arch?" % (image, url_images))

    def get_image_parameters(self, image_file_name):
        """
        Computation of image parameters from image_pattern

        :param image_file_name: pattern with parameters
        :type image_file_name: str
        :return: dict with parameters
        :rtype: dict or None
        """
        keywords = re.split(r'\{(.*?)\}', self.image_pattern)[1::2]
        matches = re.match(self.file_name, image_file_name)

        if not matches:
            return None

        return {x: matches.group(x) for x in keywords}


class FedoraImageProviderBase(ImageProviderBase):
    """
    Base Fedora Image Provider
    """

    HTML_ENCODING = 'iso-8859-1'
    url_old_images = None

    def get_image_url(self):
        if int(self.version) >= 28:
            cloud = 'Cloud'
        else:
            cloud = 'CloudImages'

        if self.url_old_images and int(self.version) <= 31:
            self.url_versions = self.url_old_images

        self.url_images = self.url_versions + '{version}/' \
            + cloud + '/{arch}/images/'
        return super(FedoraImageProviderBase, self).get_image_url()


class FedoraImageProvider(FedoraImageProviderBase):
    """
    Fedora Image Provider
    """

    name = 'Fedora'

    def __init__(self, version='[0-9]+', build='[0-9]+.[0-9]+',
                 arch=DEFAULT_ARCH):
        super(FedoraImageProvider, self).__init__(version, build, arch)
        self.url_versions = 'https://dl.fedoraproject.org/pub/fedora/linux/releases/'
        self.url_old_images = 'https://archives.fedoraproject.org/pub/archive/fedora/linux/releases/'
        self.image_pattern = 'Fedora-Cloud-Base-(?P<version>{version})-(?P<build>{build}).(?P<arch>{arch}).qcow2$'


class FedoraSecondaryImageProvider(FedoraImageProviderBase):
    """
    Fedora Secondary Image Provider
    """

    name = 'FedoraSecondary'

    def __init__(self, version='[0-9]+', build='[0-9]+.[0-9]+',
                 arch=DEFAULT_ARCH):
        super(FedoraSecondaryImageProvider, self).__init__(version, build,
                                                           arch)
        self.url_versions = 'https://dl.fedoraproject.org/pub/fedora-secondary/releases/'
        self.url_old_images = 'https://archives.fedoraproject.org/pub/archive/fedora-secondary/releases/'
        self.image_pattern = 'Fedora-Cloud-Base-(?P<version>{version})-(?P<build>{build}).(?P<arch>{arch}).qcow2$'


class CentOSImageProvider(ImageProviderBase):
    """
    CentOS Image Provider
    """

    name = 'CentOS'

    def __init__(self, version='[0-9]+', build='[0-9]{4}', arch=DEFAULT_ARCH):
        super(CentOSImageProvider, self).__init__(version, build, arch)
        self.url_versions = 'https://cloud.centos.org/centos/'
        self.url_images = self.url_versions + '{version}/images/'
        self.image_pattern = 'CentOS-(?P<version>{version})-(?P<arch>{arch})-GenericCloud-(?P<build>{build}).qcow2.xz$'

    def get_image_url(self):
        if int(self.version) >= 8:
            self.build = r'[\d\.\-]+'
            self.url_images = self.url_versions + '{version}/{arch}/images/'
            self.image_pattern = 'CentOS-(?P<version>{version})-GenericCloud-(?P<build>{build}).(?P<arch>{arch}).qcow2$'
        return super(CentOSImageProvider, self).get_image_url()


class UbuntuImageProvider(ImageProviderBase):
    """
    Ubuntu Image Provider
    """

    name = 'Ubuntu'

    def __init__(self, version='[0-9]+.[0-9]+', build=None,
                 arch=DEFAULT_ARCH):
        # Ubuntu uses 'amd64' instead of 'x86_64'
        if arch == 'x86_64':
            arch = 'amd64'
        # and 'arm64' instead of 'aarch64'
        elif arch == 'aarch64':
            arch = 'arm64'

        super(UbuntuImageProvider, self).__init__(version, build, arch)
        self.url_versions = 'http://cloud-images.ubuntu.com/releases/'
        self.url_images = self.url_versions + 'releases/{version}/release/'
        self.image_pattern = 'ubuntu-(?P<version>{version})-server-cloudimg-(?P<arch>{arch}).img'

    def get_best_version(self, versions):
        """ Return best (more recent) version """
        max_float = max([float(item) for item in versions])
        return str(f'{max_float:2.2f}')

    def get_versions(self):
        """Return all available versions for the current parameters."""
        parser = VMImageHtmlParser(self.version_pattern)
        self._feed_html_parser(self.url_versions, parser)

        resulting_versions = []
        if parser.items:
            for version in parser.items:
                max_float = float(version)
                resulting_versions.append(str(f'{max_float:2.2f}'))
        return resulting_versions


class DebianImageProvider(ImageProviderBase):
    """
    Debian Image Provider
    """

    name = 'Debian'

    def __init__(self, version=None, build=r'[\d{8}\-\d{3}]', arch=DEFAULT_ARCH):
        # Debian uses 'amd64' instead of 'x86_64'
        if arch == 'x86_64':
            arch = 'amd64'
        # and 'arm64' instead of 'aarch64'
        elif arch == 'aarch64':
            arch = 'arm64'

        table_version = {
            'buster': '10',
            'bullseye': '11',
        }

        table_codename = {
            '10': 'buster',
            '11': 'bullseye',
        }

        # Default version if none was selected, should work at least until 2023 Q3
        if version is None:
            version = "bullseye"

        # User provided a numerical version
        if version in table_codename.keys():
            version = table_codename[version]

        # If version is not a codename by now, it's wrong or unknown,
        # so let's fail early
        if (version not in table_version.keys()):
            raise ImageProviderError("Unknown version", version)

        super(DebianImageProvider, self).__init__(version, build, arch)
        self.url_versions = 'https://cloud.debian.org/images/cloud/'
        self.url_images = self.url_versions + version + '/{build}/'
        self.image_pattern = 'debian-'+table_version[version]+'-generic-(?P<arch>{arch})-{build}.qcow2$'

    def get_image_url(self):
        # Find out the build first
        parserbuild = VMImageHtmlParser(self.build)
        self._feed_html_parser(self.url_versions+self._version+"/", parserbuild)
        self.build = max(parserbuild.items)

        return super(DebianImageProvider, self).get_image_url()


class JeosImageProvider(ImageProviderBase):
    """
    JeOS Image Provider
    """

    name = 'JeOS'

    def __init__(self, version='[0-9]+', build=None,
                 arch=DEFAULT_ARCH):
        # JeOS uses '64' instead of 'x86_64'
        if arch == 'x86_64':
            arch = '64'

        super(JeosImageProvider, self).__init__(version, build, arch)
        self.url_versions = 'https://avocado-project.org/data/assets/jeos/'
        self.url_images = self.url_versions + '{version}/'
        self.image_pattern = 'jeos-(?P<version>{version})-(?P<arch>{arch}).qcow2.xz$'


class OpenSUSEImageProvider(ImageProviderBase):
    """
    OpenSUSE Image Provider
    """

    HTML_ENCODING = 'iso-8859-1'
    name = 'OpenSUSE'

    def __init__(self, version='[0-9]{2}.[0-9]{1}', build=None, arch=DEFAULT_ARCH):
        super(OpenSUSEImageProvider, self).__init__(version, build, arch)
        self.url_versions = 'https://download.opensuse.org/pub/opensuse/distribution/leap/'
        self.url_images = self.url_versions + '{version}/appliances/'

        if not build:
            self.image_pattern = 'openSUSE-Leap-(?P<version>{version})-JeOS.(?P<arch>{arch})-OpenStack-Cloud.qcow2$'

        else:
            self.image_pattern = 'openSUSE-Leap-(?P<version>{version})-JeOS.(?P<arch>{arch})-{version}' \
                                 '-OpenStack-Cloud-Build(?P<build>{build}).qcow2$'

    @staticmethod
    def _convert_version_numbers(versions):
        """
        Return float instead of strings
        """
        return [float(v) for v in versions]

    def get_versions(self):
        versions = super(OpenSUSEImageProvider, self).get_versions()
        return self._convert_version_numbers(versions)

    def get_best_version(self, versions):
        version_numbers = self._convert_version_numbers(versions)
        if str(self._version).startswith('4'):
            version_numbers = [v for v in version_numbers if v >= 40.0]
        else:
            version_numbers = [v for v in version_numbers if v < 40.0]
        return max(version_numbers)


class CirrOSImageProvider(ImageProviderBase):
    """
    CirrOS Image Provider

    CirrOS is a Tiny OS that specializes in running on a cloud.
    """

    name = 'CirrOS'

    def __init__(self, version=r'[0-9]+\.[0-9]+\.[0-9]+', build=None, arch=DEFAULT_ARCH):
        super(CirrOSImageProvider, self).__init__(version=version, build=build, arch=arch)
        self.url_versions = 'https://download.cirros-cloud.net/'
        self.url_images = self.url_versions + '{version}/'
        self.image_pattern = 'cirros-{version}-{arch}-disk.img$'


class Image:
    def __init__(self, name, url, version, arch, build, checksum, algorithm,
                 cache_dir, snapshot_dir=None):
        """
        Creates an instance of Image class.

        :param name: Name of image.
        :type name: str
        :param url: The url where the image can be fetched from.
        :type url: str
        :param version: Version of image.
        :type version: int
        :param arch: Architecture of the system image.
        :type arch: str
        :param build: Build of the system image.
        :type build: str
        :param checksum: Hash of the system image to match after download.
        :type checksum: str
        :param algorithm: Hash type, used when the checksum is provided.
        :type algorithm: str
        :param cache_dir: Local system path where the base images will be held.
        :type cache_dir: str or iterable
        :param snapshot_dir: Local system path where the snapshot images
                            will be held.  Defaults to cache_dir if none is given.
        :type snapshot_dir: str
        """
        self.name = name
        self.url = url
        self.version = version
        self.arch = arch
        self.build = build
        self.checksum = checksum
        self.algorithm = algorithm
        self.cache_dir = cache_dir
        self.snapshot_dir = snapshot_dir

        self._path = None
        self._base_image = None

    @property
    def path(self):
        return self._path or self.get()

    @property
    def base_image(self):
        return self._base_image or self.download()

    def __repr__(self):
        return "<%s name=%s version=%s arch=%s>" % (self.__class__.__name__,
                                                    self.name,
                                                    self.version,
                                                    self.arch)

    def download(self):
        metadata = {"type": "vmimage", "name": self.name,
                    "version": self.version, "arch": self.arch,
                    "build": self.build}
        if isinstance(self.cache_dir, str):
            cache_dirs = [self.cache_dir]
        else:
            cache_dirs = self.cache_dir
        asset_path = asset.Asset(name=self.url,
                                 asset_hash=self.checksum,
                                 algorithm=self.algorithm,
                                 locations=None,
                                 cache_dirs=cache_dirs,
                                 expire=None,
                                 metadata=metadata).fetch()

        if archive.is_archive(asset_path):
            uncompressed_path = os.path.splitext(asset_path)[0]
            asset_path = archive.uncompress(asset_path, uncompressed_path)
        self._base_image = asset_path
        return self._base_image

    def get(self):
        self.download()
        self._path = self._take_snapshot()
        return self._path

    def _take_snapshot(self):
        """
        Takes a snapshot from the current image.
        """
        if QEMU_IMG is None:
            qemu_img = utils_path.find_command('qemu-img')
        else:
            qemu_img = QEMU_IMG
        name, extension = os.path.splitext(self.base_image)
        new_image = '%s-%s%s' % (name, str(uuid.uuid4()).split('-')[0],
                                 extension)
        if self.snapshot_dir is not None:
            new_image = os.path.join(self.snapshot_dir,
                                     os.path.basename(new_image))
        cmd = '%s create -f qcow2 -b %s -F qcow2 %s' % (qemu_img,
                                                        self.base_image,
                                                        new_image)
        process.run(cmd)
        return new_image

    @classmethod
    def from_parameters(cls, name=None, version=None, build=None, arch=None,
                        checksum=None, algorithm=None, cache_dir=None,
                        snapshot_dir=None):
        """
        Returns an Image, according to the parameters provided.

        :param name: (optional) Name of the Image Provider, usually matches
                     the distro name.
        :param version: (optional) Version of the system image.
        :param build: (optional) Build number of the system image.
        :param arch: (optional) Architecture of the system image.
        :param checksum: (optional) Hash of the system image to match after
                         download.
        :param algorithm: (optional) Hash type, used when the checksum is
                          provided.
        :param cache_dir: (optional) Local system path where the base
                          images will be held.
        :param snapshot_dir: (optional) Local system path where the snapshot
                             images will be held.  Defaults to cache_dir if
                             none is given.

        :returns: Image instance that can provide the image
                  according to the parameters.
        """
        provider = get_best_provider(name, version, build, arch)

        if cache_dir is None:
            cache_dir = tempfile.gettempdir()
        try:
            return cls(name=provider.name, url=provider.get_image_url(),
                       version=provider.version, arch=provider.arch,
                       checksum=checksum, algorithm=algorithm,
                       build=provider.build, cache_dir=cache_dir,
                       snapshot_dir=snapshot_dir)
        except ImageProviderError:
            pass

        raise AttributeError('Provider not available')


def get(name=None, version=None, build=None, arch=None, checksum=None,
        algorithm=None, cache_dir=None, snapshot_dir=None):
    """This method is deprecated. Use Image.from_parameters()."""
    warnings.warn("deprecated, use Image.from_parameters() instead.",
                  DeprecationWarning)
    return Image.from_parameters(name, version, build, arch, checksum,
                                 algorithm, cache_dir, snapshot_dir)


def get_best_provider(name=None, version=None, build=None, arch=None):
    """
    Wrapper to get parameters of the best Image Provider, according to
    the parameters provided.

    :param name: (optional) Name of the Image Provider, usually matches
                 the distro name.
    :param version: (optional) Version of the system image.
    :param build: (optional) Build number of the system image.
    :param arch: (optional) Architecture of the system image.

    :returns: Image Provider
    """

    if name is not None:
        name = name.lower()

    provider_args = {}
    if version is not None:
        provider_args['version'] = version
    if build is not None:
        provider_args['build'] = build
    if arch is not None:
        provider_args['arch'] = arch
        if name == 'fedora' and arch in ('ppc64', 'ppc64le', 's390x'):
            name = 'fedorasecondary'

    for provider in IMAGE_PROVIDERS:
        if name is None or name == provider.name.lower():
            try:
                return provider(**provider_args)
            except ImageProviderError:
                pass

    raise AttributeError('Provider not available')


def list_providers():
    """
    List the available Image Providers
    """
    return set(_ for _ in globals().values()
               if (isinstance(_, type) and
                   issubclass(_, ImageProviderBase) and
                   hasattr(_, 'name')))


#: List of available providers classes
IMAGE_PROVIDERS = list_providers()
