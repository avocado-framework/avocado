#!/usr/bin/python

from avocado import Test
from avocado import main
from avocado.utils import kernel_build


class LinuxBuildTest(Test):

    """
    Execute the Linux Build test.

    :param linux_version: kernel version to be built
    :param linux_config: name of the config file located in deps path
    """

    def setUp(self):
        kernel_version = self.params.get('linux_version', default='3.19.8')
        linux_config = self.params.get('linux_config', default=None)
        config_path = self.get_data_path(linux_config)
        self.linux_build = kernel_build.KernelBuild(kernel_version,
                                                    config_path,
                                                    self.srcdir)
        self.linux_build.download()
        self.linux_build.uncompress()
        self.linux_build.configure()

    def test(self):
        self.linux_build.build()


if __name__ == "__main__":
    main()
