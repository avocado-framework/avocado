#!/usr/bin/python

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

import os
import logging
import shutil

from . import download, archive, build


log = logging.getLogger('avocado.test')


class KernelBuild(object):

    """
    Build the Linux Kernel from official tarballs.
    """

    url = 'https://www.kernel.org/pub/linux/kernel/v3.x/'
    source = 'linux-{version}.tar.gz'

    def __init__(self, version, config_path, work_dir):
        """
        Creates an instance of :class:`KernelBuild`.

        :param version: kernel version ("3.14.5").
        :param config_path: path to config file.
        :param work_dir: work directory.
        :return: None.
        """
        self.version = version
        self.config_path = config_path
        self.work_dir = work_dir

    def __repr__(self):
        return "KernelBuild('%s, %s, %s')" % (self.version,
                                              self.config_path,
                                              self.work_dir)

    def download(self):
        """
        Download kernel source.
        """
        self.kernel_file = KernelBuild.source.format(version=self.version)
        full_url = KernelBuild.url + KernelBuild.source.format(version=self.version)
        path = os.path.join(self.work_dir, self.kernel_file)
        if os.path.isfile(path):
            log.info("File '%s' exists, will not download!", path)
        else:
            log.info("Downloading '%s'...", full_url)
            download.url_download(full_url, path)

    def uncompress(self):
        """
        Uncompress kernel source.
        """
        log.info("Uncompressing tarball")
        path = os.path.join(self.work_dir, self.kernel_file)
        archive.extract(path, self.work_dir)

    def configure(self):
        """
        Configure/prepare kernel source to build.
        """
        self.linux_dir = os.path.join(self.work_dir, 'linux-%s' % self.version)
        #log.info("Running make mrproper")
        build.make(self.linux_dir, extra_args='mrproper')
        dotconfig = os.path.join(self.linux_dir, '.config')
        shutil.copy(self.config_path, dotconfig)

    def build(self):
        """
        Build kernel from source.
        """
        log.info("Starting build the kernel")
        build.make(self.linux_dir, extra_args='oldconfig')
        build.make(self.linux_dir, extra_args='dep')
        build.make(self.linux_dir, extra_args='bzImage')
