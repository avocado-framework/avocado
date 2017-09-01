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
import string
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
    def __init__(self, pattern):
        HTMLParser.__init__(self)
        self.versions = []
        self.pattern = pattern

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        for attr in attrs:
            if attr[0] == 'href' and re.match(self.pattern, attr[1]):
                self.versions.append(attr[1].strip('/'))


class ImageBase(object):
    def __init__(self, **kwargs):
        self.path = None
        self.url = None

        self.url_versions = None
        self.url_images = None
        self.image = None

        self.default_version = None
        self.default_build = None
        self.default_arch = None

        self.args = {}
        self.initargs = kwargs

    def get(self):
        self.url = self.get_url()

        asset_path = asset.Asset(name=self.url,
                                 asset_hash=self.args['checksum'],
                                 algorithm=self.args['algorithm'],
                                 locations=None,
                                 cache_dirs=[self.args['cache_dir']],
                                 expire=None).fetch()

        if os.path.splitext(asset_path)[1] == '.xz':
            if LZMA_CAPABLE:
                asset_path = self._extract(asset_path)
            else:
                raise ImageProviderError('Cannot uncompress image')

        self.path = self._create_backed_image(asset_path)
        return self.path

    def get_url(self):
        # Did user pass all the args required to create the URL?
        image_url = self.url_images + self.image
        required_args = []
        for key in string.Formatter().parse(image_url):
            if key[1] is not None:
                required_args.append(key[1])
        all_args = True
        for required_arg in required_args:
            if (required_arg not in self.initargs or
                    self.initargs[required_arg] is None):
                all_args = False
        # In that case, URL is ready
        if all_args:
            return image_url.format(**self.initargs)

        # Otherwise, we have to probe it externally
        # Getting the requested version, if available
        version = self.get_version()
        # Getting the image URL
        return self.get_image(version)

    def get_version(self):
        pattern = '^%s/$' % self.args['version']

        parser = VMImageHtmlParser(pattern)
        try:
            parser.feed(urllib2.urlopen(self.url_versions).read())
        except:
            raise ImageProviderError('Cannot open %s' % self.url_versions)
        if parser.versions:
            resulting_versions = []
            for version in parser.versions:
                try:
                    resulting_versions.append(int(version))
                except ValueError:
                    try:
                        resulting_versions.append(float(version))
                    except ValueError:
                        resulting_versions.append(version)
            return max(resulting_versions)
        else:
            raise ImageProviderError('Version %s not available at %s' %
                                     (self.default_version, self.url_versions))

    def get_image(self, version):
        url_images = self.url_images.format(version=version,
                                            build=self.args['build'],
                                            arch=self.args['arch'])
        image = self.image.format(version=version,
                                  build=self.args['build'],
                                  arch=self.args['arch'])
        parser = VMImageHtmlParser(image)
        try:
            content = urllib2.urlopen(url_images).read()
            parser.feed(content)
        except:
            raise ImageProviderError('Cannot open %s' % url_images)
        if parser.versions:
            return url_images + max(parser.versions)
        else:
            raise ImageProviderError("No images matching '%s' at '%s'" %
                                     (image, url_images))

    def remove(self):
        """
        Removes the VM Image
        """
        if self.path is not None:
            os.remove(self.path)
            self.path = None

    @staticmethod
    def _create_backed_image(source_image):
        """
        Creates a Qcow2 backed image using the original image
        as backing file.
        """
        qemu_img = utils_path.find_command('qemu-img')

        name, extension = os.path.splitext(source_image)
        new_image = '%s-%s%s' % (name, str(uuid.uuid4()).split('-')[0],
                                 extension)
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


class FedoraImageProvider(ImageBase):

    name = 'Fedora'

    def __init__(self, **kwargs):
        super(FedoraImageProvider, self).__init__(**kwargs)
        # Here you can use string formatting tags corresponding to the
        # arguments accepted (version, build and arch).
        self.url_versions = 'https://dl.fedoraproject.org/pub/fedora/linux/releases/'
        self.url_images = self.url_versions + '{version}/CloudImages/{arch}/images/'
        self.image = 'Fedora-Cloud-Base-{version}-{build}.{arch}.qcow2'

        # Set the defaults to be used when the arguments are
        # not provided. If you don't want to force a version,
        # you can provide a regular expression that matches the
        # corresponding format and we will get the highest
        # occurrence of that expression.
        self.default_version = '[0-9]+'  # 22/23/24/...
        self.default_build = '[0-9]+.[0-9]+'  # 1.4/5.1/5.2/...
        self.default_arch = 'x86_64'

        # Dictionary of expected arguments and their values
        self.args = {'version': kwargs.get('version', self.default_version),
                     'build': kwargs.get('build', self.default_build),
                     'arch': kwargs.get('arch', self.default_arch),
                     'checksum': kwargs.get('checksum', None),
                     'algorithm': kwargs.get('algorithm', None),
                     'cache_dir': kwargs.get('cache_dir',
                                             tempfile.gettempdir())}


class FedoraSecondaryImageProvider(ImageBase):

    name = 'FedoraSecondary'

    def __init__(self, **kwargs):
        super(FedoraSecondaryImageProvider, self).__init__(**kwargs)
        # Here you can use string formatting tags corresponding to the
        # arguments accepted (version, build and arch).
        self.url_versions = 'https://dl.fedoraproject.org/pub/fedora-secondary/releases/'
        self.url_images = self.url_versions + '{version}/CloudImages/{arch}/images/'
        self.image = 'Fedora-Cloud-Base-{version}-{build}.{arch}.qcow2'

        # Set the defaults to be used when the arguments are
        # not provided. If you don't want to force a version,
        # you can provide a regular expression that matches the
        # corresponding format and we will get the highest
        # occurrence of that expression.
        self.default_version = '[0-9]+'  # 22/23/24/...
        self.default_build = '[0-9]+.[0-9]+'  # 1.4/5.1/5.2/...
        self.default_arch = 'aarch64'

        # Dictionary of expected arguments and their values
        self.args = {'version': kwargs.get('version', self.default_version),
                     'build': kwargs.get('build', self.default_build),
                     'arch': kwargs.get('arch', self.default_arch),
                     'checksum': kwargs.get('checksum', None),
                     'algorithm': kwargs.get('algorithm', None),
                     'cache_dir': kwargs.get('cache_dir',
                                             tempfile.gettempdir())}


class CentOSImageProvider(ImageBase):

    name = 'CentOS'

    def __init__(self, **kwargs):
        super(CentOSImageProvider, self).__init__(**kwargs)
        # Here you can use string formatting tags corresponding to the
        # arguments accepted (version, build and arch).
        self.url_versions = 'https://cloud.centos.org/centos/'
        self.url_images = self.url_versions + '{version}/images/'
        self.image = 'CentOS-{version}-{arch}-GenericCloud-{build}.qcow2.xz'

        # Set the defaults to be used when the arguments are
        # not provided. If you don't want to force a version,
        # you can provide a regular expression that matches the
        # corresponding format and we will get the highest
        # occurrence of that expression.
        self.default_version = '[0-9]+'  # 5/6/7/...
        self.default_build = '[0-9]{4}'  # 1704/1706/...
        self.default_arch = 'x86_64'

        # Dictionary of expected arguments and their values
        self.args = {'version': kwargs.get('version', self.default_version),
                     'build': kwargs.get('build', self.default_build),
                     'arch': kwargs.get('arch', self.default_arch),
                     'checksum': kwargs.get('checksum', None),
                     'algorithm': kwargs.get('algorithm', None),
                     'cache_dir': kwargs.get('cache_dir',
                                             tempfile.gettempdir())}


class UbuntuImageProvider(ImageBase):

    name = 'Ubuntu'

    def __init__(self, **kwargs):
        super(UbuntuImageProvider, self).__init__(**kwargs)
        # Here you can use string formatting tags corresponding to the
        # arguments accepted (version, build and arch).
        self.url_versions = 'http://cloud-images.ubuntu.com/releases/'
        self.url_images = self.url_versions + 'releases/{version}/release/'
        self.image = 'ubuntu-{version}-server-cloudimg-{arch}.img'

        # Set the defaults to be used when the arguments are
        # not provided. If you don't want to force a version,
        # you can provide a regular expression that matches the
        # corresponding format and we will get the highest
        # occurrence of that expression.
        self.default_version = '[0-9]+.[0-9]+'  # 16.10/17.04/...
        self.default_build = None  # Ubuntu doesn't seem to mark builds
        self.default_arch = 'amd64'

        # Dictionary of expected arguments and their values
        self.args = {'version': kwargs.get('version', self.default_version),
                     'build': kwargs.get('build', self.default_build),
                     'arch': kwargs.get('arch', self.default_arch),
                     'checksum': kwargs.get('checksum', None),
                     'algorithm': kwargs.get('algorithm', None),
                     'cache_dir': kwargs.get('cache_dir',
                                             tempfile.gettempdir())}


class DebianImageProvider(ImageBase):

    name = 'Debian'

    def __init__(self, **kwargs):
        super(DebianImageProvider, self).__init__(**kwargs)
        # Here you can use string formatting tags corresponding to the
        # arguments accepted (version, build and arch).
        self.url_versions = 'https://cdimage.debian.org/cdimage/openstack/'
        self.url_images = self.url_versions + '/{version}/'
        self.image = 'debian-{version}-openstack-{arch}.qcow2$'

        # Set the defaults to be used when the arguments are
        # not provided. If you don't want to force a version,
        # you can provide a regular expression that matches the
        # corresponding format and we will get the highest
        # occurrence of that expression.
        self.default_version = '[0-9]+.[0-9]+.[0-9]+-.*'  # 9.1.4-20170830
        self.default_build = None  # Build is part of the image version
        self.default_arch = 'amd64'

        # Dictionary of expected arguments and their values
        self.args = {'version': kwargs.get('version', self.default_version),
                     'build': kwargs.get('build', self.default_build),
                     'arch': kwargs.get('arch', self.default_arch),
                     'checksum': kwargs.get('checksum', None),
                     'algorithm': kwargs.get('algorithm', None),
                     'cache_dir': kwargs.get('cache_dir',
                                             tempfile.gettempdir())}


class ImageProviderProxy(object):
    def __init__(self):
        self.providers_list = []
        self.providers_list.append(FedoraImageProvider)
        self.providers_list.append(FedoraSecondaryImageProvider)
        self.providers_list.append(CentOSImageProvider)
        self.providers_list.append(UbuntuImageProvider)
        self.providers_list.append(DebianImageProvider)

    def get(self, name=None, **kwargs):
        # No name, return the first registered provider
        if name is None and self.providers_list:
            return self.providers_list[0](**kwargs).get()
        for provider in self.providers_list:
            if provider.name.lower() == name.lower():
                return provider(**kwargs).get()
        raise AttributeError('No such provider (%s)' % name)

    def list_providers(self):
        return self.providers_list


get = ImageProviderProxy().get
list_providers = ImageProviderProxy().list_providers
