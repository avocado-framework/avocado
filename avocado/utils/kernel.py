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

"""
Provides utilities for the Linux kernel.
"""

import logging
import multiprocessing
import os
import shutil
import tempfile

from pkg_resources import packaging

from . import archive, asset, build, distro, process

LOG = logging.getLogger('avocado.test')


class KernelBuild:

    """
    Build the Linux Kernel from official tarballs.
    """

    URL = 'https://www.kernel.org/pub/linux/kernel/v{major}.x/'
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
        self.asset_path = None
        self.version = version
        self.config_path = config_path
        self.distro = distro.detect()
        if work_dir is None:
            work_dir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.work_dir = work_dir
        if data_dirs is not None:
            self.data_dirs = data_dirs
        else:
            self.data_dirs = [self.work_dir]
        self._build_dir = os.path.join(self.work_dir, 'linux-%s' % self.version)

    def __repr__(self):
        return "KernelBuild('%s, %s, %s')" % (self.version,
                                              self.config_path,
                                              self.work_dir)

    @property
    def vmlinux(self):
        """
        Return the vmlinux path if the file exists
        """
        if not self.build_dir:
            return None
        vmlinux_path = os.path.join(self.build_dir, 'vmlinux')
        if os.path.isfile(vmlinux_path):
            return vmlinux_path
        return None

    @property
    def build_dir(self):
        """
        Return the build path if the directory exists
        """
        if os.path.isdir(self._build_dir):
            return self._build_dir
        return None

    def _build_kernel_url(self, base_url=None):
        kernel_file = self.SOURCE.format(version=self.version)
        if base_url is None:
            base_url = self.URL.format(major=self.version.split('.', 1)[0])
        return base_url + kernel_file

    def download(self, url=None):
        """
        Download kernel source.

        :param url: override the url from where to fetch the kernel
                    source tarball
        :type url: str or None
        """
        full_url = self._build_kernel_url(base_url=url)
        self.asset_path = asset.Asset(full_url, asset_hash=None,
                                      algorithm=None, locations=None,
                                      cache_dirs=self.data_dirs).fetch()

    def uncompress(self):
        """
        Uncompress kernel source.

        :raises: Exception in case the tarball is not downloaded
        """
        if self.asset_path:
            LOG.info("Uncompressing tarball")
            archive.extract(self.asset_path, self.work_dir)
        else:
            raise Exception("Unable to find the tarball")

    def configure(self, targets=('defconfig'), extra_configs=None):
        """
        Configure/prepare kernel source to build.

        :param targets: configuration targets. Default is 'defconfig'.
        :type targets: list of str
        :param extra_configs: additional configurations in the form of
                              CONFIG_NAME=VALUE.
        :type extra_configs: list of str
        """
        build.make(self._build_dir, extra_args='-C %s mrproper' %
                   self._build_dir)
        if self.config_path is not None:
            dotconfig = os.path.join(self._build_dir, '.config')
            shutil.copy(self.config_path, dotconfig)
            build.make(self._build_dir, extra_args='-C %s olddefconfig' %
                       self._build_dir)
        else:
            if isinstance(targets, list):
                _targets = " ".join(targets)
            else:
                _targets = targets
            build.make(self.build_dir,
                       extra_args='-C %s %s' % (self.build_dir, _targets))
        if extra_configs:
            with tempfile.NamedTemporaryFile(mode='w+t',
                                             prefix='avocado_') as config_file:
                config_file.write('\n'.join(extra_configs))
                config_file.flush()
                cmd = ['cd', self._build_dir, '&&',
                       './scripts/kconfig/merge_config.sh', '.config',
                       config_file.name]
                process.run(" ".join(cmd), shell=True)

    def build(self, binary_package=False, njobs=multiprocessing.cpu_count()):
        """
        Build kernel from source.

        :param binary_package: when True, the appropriate
                                  platform package is built
                                  for install() to use
        :type binary_pacakge: bool
        :param njobs: number of jobs. It is mapped to the -j option from make.
                      If njobs is None then do not limit the number of jobs
                      (e.g. uses -j without value). The -j is omitted if a
                      value equal or less than zero is passed. Default value
                      is set to `multiprocessing.cpu_count()`.
        :type njobs: int or None
        """
        make_args = []
        LOG.info("Starting build the kernel")

        if njobs is None:
            make_args.append('-j')
        elif njobs > 0:
            make_args.extend(['-j', str(njobs)])
        make_args.extend(['-C', self._build_dir])

        if binary_package is True:
            if self.distro.name == "Ubuntu":
                make_args.append("deb-pkg")

        build.make(self._build_dir, extra_args=" ".join(make_args))

    def install(self):
        """
        Install built kernel.
        """
        LOG.info("Starting kernel install")
        if self.distro.name == "Ubuntu":
            process.run('dpkg -i %s/*.deb' %
                        self.work_dir, shell=True, sudo=True)
        else:
            LOG.info("Skipping kernel install")

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
    os_version = packaging.version.parse(os.uname()[2])
    version = packaging.version.parse(version)
    assert os_version > version, "Old kernel"
