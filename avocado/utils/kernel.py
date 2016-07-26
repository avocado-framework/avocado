#!/usr/bin/env python

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
# Author: Santhosh G <santhog4@linux.vnet.ibm.com>

import os
import shutil
import logging
import tempfile
from distutils.version import LooseVersion

from . import asset, archive, build
from . import data_structures

log = logging.getLogger('avocado.test')


class KernelBuild(object):

    """
    Build the Linux Kernel from official tarballs.
    """

    URLS = ['https://www.kernel.org/pub/linux/kernel/v3.x/',
            'https://www.kernel.org/pub/linux/kernel/v4.x/']

    SOURCE = 'linux-{version}.tar.gz'

    def __init__(self, version, config_path=None, mirrors=None, work_dir=None,
                 data_dirs=None):
        """
        Creates an instance of :class:`KernelBuild`.

        :param version: kernel version ("3.19.8").
        :param config_path: path to config file.
        :param mirrors: list of mirrors to try
        :param work_dir: work directory.
        :param data_dirs: list of directories to keep the downloaded kernel
        :return: None.
        """
        self.version = version
        self.config_path = config_path
        if work_dir is None:
            work_dir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.work_dir = work_dir
        if data_dirs is not None:
            self.data_dirs = data_dirs
        else:
            self.data_dirs = [self.work_dir]
        self.build_dir = os.path.join(self.work_dir, 'build')
        if not os.path.isdir(self.build_dir):
            os.makedirs(self.build_dir)

        self.mirrors = []
        if mirrors is not None:
            for item in mirrors:
                if item.endswith('/'):
                    self.mirrors.append(item)
                else:
                    self.mirrors.append(item + '/')

    def __repr__(self):
        return "KernelBuild('%s, %s, %s')" % (self.version,
                                              self.config_path,
                                              self.work_dir)

    def download(self, name=None, asset_hash=None, algorithm='sha1',
                    locations=None, expire=None):
        """
        Download kernel source.
        Method call the utils.asset in order to fetch and asset file
        supporting hash check, caching and multiple locations.

        :param name: the asset filename or URL
        :param asset_hash: asset hash (optional)
        :param algorithm: hash algorithm (optional, defaults to sha1)
        :param locations: list of URLs from where the asset can be
                          fetched (optional)
        :param expire: time for the asset to expire
        """

        if name is None:
            self.kernel_file = self.SOURCE.format(version=self.version)
        else:
            self.kernel_file = name

        if locations is None:
            locations = []
            for item in self.mirrors:
                locations.append(item + self.kernel_file)
            for item in self.URLS:
                locations.append(item + self.kernel_file)

        if expire is not None:
            expire = data_structures.time_to_seconds(str(expire))

        self.asset_path = asset.Asset(self.kernel_file,
                                      asset_hash,
                                      algorithm, locations,
                                      self.data_dirs,
                                      expire).fetch()

        
    def uncompress(self):
        """
        Uncompress kernel source.
        """
        log.info("Uncompressing tarball")
        archive.extract(self.asset_path, self.work_dir)

    def configure(self):
        """
        Configure/prepare kernel source to build.
        """
        self.linux_dir = os.path.join(self.work_dir, 'linux-%s' % self.version)
        build.make(self.linux_dir, extra_args='O=%s mrproper' % self.build_dir)
        log.info("Apply kernel config")
        if self.config_path is not None:
            dotconfig = os.path.join(self.linux_dir, '.config')
            shutil.copy(self.config_path, dotconfig)
            build.make(self.linux_dir, extra_args='O=%s olddefconfig' % self.build_dir)
        else:
            build.make(self.linux_dir, extra_args='O=%s defconfig' % self.build_dir)

    def build(self, build_target='', extra_args=''):
        """
        Build kernel from source.
        """
        log.info("Starting build the kernel")
        build.make(self.linux_dir, extra_args='O=%s %s %s' % \
                   (self.build_dir, extra_args, build_target), \
                   allow_output_check = 'all')

    def __del__(self):
        shutil.rmtree(self.work_dir)


def check_version(version):
    """
    This utility function compares the current kernel version with
    the version parameter and gives assertion error if the version
    parameter is greater.

    :type version: string
    :param version: version to be compared with current kernel version
    """
    assert LooseVersion(os.uname()[2]) > LooseVersion(version), "Old kernel"
