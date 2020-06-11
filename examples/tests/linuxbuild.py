from avocado import Test
from avocado.utils import kernel


class LinuxBuildTest(Test):

    """
    Execute the Linux Build test.

    :avocado: tags=requires_c_compiler

    :param linux_version: kernel version to be built
    :param linux_config: name of the config file located in a data directory
    """

    def setUp(self):
        kernel_src_url = self.params.get('linux_src_url', default='https://www.kernel.org/pub/linux/kernel/v5.x/')
        kernel_version = self.params.get('linux_version', default='5.4.1')
        linux_config = self.params.get('linux_config', default=None)
        self.do_kernel_install = self.params.get('do_kernel_install', default=None)
        if linux_config is not None:
            linux_config = self.get_data(linux_config)
        if linux_config is None:
            self.cancel('Test is missing data file %s' % linux_config)

        self.linux_build = kernel.KernelBuild(kernel_version,
                                              linux_config,
                                              self.workdir,
                                              self.cache_dirs)
        self.linux_build.download(kernel_src_url)
        self.linux_build.uncompress()
        self.linux_build.configure()

    def test(self):
        self.linux_build.build(True if self.do_kernel_install is not None else False)
        if self.do_kernel_install is not None:
            self.linux_build.install()
