#!/usr/bin/python

import avocado

from avocado.linux import kernel_build


class LinuxBuildTest(avocado.Test):

    """
    Execute the Linux Build test.
    """
    default_params = {'linux_version': '3.14.5',
                      'linux_config': 'config'}

    def setup(self):
        kernel_version = self.params.linux_version
        config_path = self.get_data_path('config')
        self.linux_build = kernel_build.KernelBuild(kernel_version,
                                                    config_path,
                                                    self.srcdir)
        self.linux_build.download()
        self.linux_build.uncompress()
        self.linux_build.configure()

    def action(self):
        self.linux_build.build()


if __name__ == "__main__":
    avocado.main()
