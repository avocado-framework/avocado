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

log = logging.getLogger('avocado.test')


class KernelBuild(object):

    """
    Build the Linux Kernel from official tarballs.
    """

    URL = 'https://www.kernel.org/pub/linux/kernel/v3.x/'
    SOURCE = 'linux-{version}.tar.gz'

    def __init__(self, version, config_path=None, work_dir=None,
                 data_dirs=None):
        """
        Creates an instance of :class:`KernelBuild`.

        :param version: kernel version ("3.19.8").
        :param config_path: path to config file.
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

    def __repr__(self):
        return "KernelBuild('%s, %s, %s')" % (self.version,
                                              self.config_path,
                                              self.work_dir)

    def download(self):
        """
        Download kernel source.
        """
        self.kernel_file = self.SOURCE.format(version=self.version)
        full_url = self.URL + self.SOURCE.format(version=self.version)
        self.asset_path = asset.Asset(full_url, asset_hash=None,
                                      algorithm=None, locations=None,
                                      cache_dirs=self.data_dirs).fetch()

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
        if self.config_path is not None:
            dotconfig = os.path.join(self.linux_dir, '.config')
            shutil.copy(self.config_path, dotconfig)

    def build(self):
        """
        Build kernel from source.
        """
        log.info("Starting build the kernel")
        if self.config_path is None:
            build.make(self.linux_dir, extra_args='O=%s defconfig' % self.build_dir)
        else:
            build.make(self.linux_dir, extra_args='O=%s olddefconfig' % self.build_dir)
        build.make(self.linux_dir, extra_args='O=%s' % self.build_dir)

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
