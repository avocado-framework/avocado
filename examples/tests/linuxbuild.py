#!/usr/bin/env python

import os

from avocado import Test
from avocado import main
from avocado.utils import kernel


class LinuxBuildTest(Test):

    """
    Execute the Linux Build test.

    :avocado: tags=requires_c_compiler

    :param linux_version: kernel version to be built
    :param linux_config: name of the config file located in deps path
    """

    def setUp(self):
        kernel_version = self.params.get('linux_version', default='3.19.8')
        linux_config = self.params.get('linux_config', default=None)
        if linux_config is not None:
            linux_config = os.path.join(self.datadir, linux_config)

        self.linux_build = kernel.KernelBuild(kernel_version,
                                              linux_config,
                                              self.srcdir,
                                              self.cache_dirs)
        self.linux_build.download()
        self.linux_build.uncompress()
        self.linux_build.configure()

    def test(self):
        self.linux_build.build()


if __name__ == "__main__":
    main()
