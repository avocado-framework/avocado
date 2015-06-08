#!/usr/bin/python

from avocado import Test
from avocado import main
from avocado.linux import kernel_build


class LinuxBuildTest(Test):

    """
    Execute the Linux Build test.
    """

    def setUp(self):
        kernel_version = self.params.get('linux_version', default='3.14.5')
        linux_config = self.params.get('linux_config', default='config')
        config_path = self.get_data_path(linux_config)
        self.linux_build = kernel_build.KernelBuild(kernel_version,
                                                    config_path,
                                                    self.srcdir)
        self.linux_build.download()
        self.linux_build.uncompress()
        self.linux_build.configure()

    def runTest(self):
        self.linux_build.build()


if __name__ == "__main__":
    main()
