#!/usr/bin/env python

import os

from avocado import Test
from avocado import main
from avocado.utils import kernel

# External parameters should be passed via multiplex file
# example: 
# avocado run linuxbuild.py -m /usr/share/avocado/tests/linuxbuild.py.data/linuxbuild.yaml

class LinuxBuildTest(Test):

    """
    Execute the Linux Build test.

    :param linux_version: kernel version to be built
    :param linux_config: name of the config file located in deps path
    :param linux_file: the asset filename or URL
    :param asset_hash: asset hash (optional)
    :param algorithm: hash algorithm (optional, defaults to sha1)
    :param locations: list of URLs from where the asset can be
                          fetched (optional)
    :param build_target: built target (bzImage,modules,etc..)
    :param build_args: extra arguments for make

    """

    def setUp(self):
        kernel_version = self.params.get('linux_version', default='3.19.8')
        linux_config = self.params.get('linux_config', default=None)
        linux_file= self.params.get('linux_file', default=None)
        asset_hash = self.params.get('asset_hash', default=None)
        algorithm= self.params.get('hash_algo', default='sha1')
        mirrors= self.params.get('mirrors', default=None)
        locations= self.params.get('locations', default=None)

        self.build_target= self.params.get('build_target', default='')
        self.extra_args= self.params.get('build_args', default='')


        if linux_config is not None:
            linux_config = os.path.join(self.datadir, linux_config)
        
        self.linux_build = kernel.KernelBuild(kernel_version,
                                              linux_config,
                                              mirrors,
                                              self.srcdir,
                                              self.cache_dirs)
        self.linux_build.download(linux_file,
                                  asset_hash, algorithm,
                                  locations)
        self.linux_build.uncompress()
        self.linux_build.configure()

    def test(self):
        self.linux_build.build(self.build_target, self.extra_args)


if __name__ == "__main__":
    main()
