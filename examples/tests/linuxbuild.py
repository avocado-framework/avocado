#!/usr/bin/python

from avocado import test
from avocado.core import job
from avocado.linux import kernel_build


class LinuxBuildTest(test.Test):

    """
    Execute the Linux Build test.
    """

    def setUp(self):
        kernel_version = self.params.get('linux_version', '3.14.5')
        linux_config = self.params.get('linux_config', 'config')
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
    job.main()
