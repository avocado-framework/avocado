from avocado import Test
from avocado import fail_on
from avocado.utils import vmimage
from avocado.utils import process

from urllib.request import urlopen
from urllib.error import HTTPError


class Base(Test):
    """
    Tests if avocado.utils.vmimage providers are current and can reach images

    :avocado: tags=network
    """

    DEFAULTS = {'name': 'fedora',
                'version': '31',
                'build': None,
                'arch': 'x86_64'}

    def setUp(self):
        self.vmimage_name = self.params.get('name',
                                            default=self.DEFAULTS.get('name'))
        self.vmimage_version = self.params.get('version',
                                               default=self.DEFAULTS.get('version'))
        self.vmimage_build = self.params.get('build',
                                             default=self.DEFAULTS.get('build'))
        # This is the "standard" archtiecture name
        arch = self.params.get('arch', path='*/architectures/*',
                               default=self.DEFAULTS.get('arch'))
        # Distros may use slightly different values for their architecture names.
        # For instance, Cirros ppc images are called powerpc, so we look
        distro_arch_path = '/run/distro/%s/%s/*' % (self.vmimage_name, arch)
        self.vmimage_arch = self.params.get('arch', path=distro_arch_path, default=arch)


class Provider(Base):
    def setUp(self):
        super(Provider, self).setUp()
        self.vmimage_provider = vmimage.get_best_provider(self.vmimage_name,
                                                          self.vmimage_version,
                                                          self.vmimage_build,
                                                          self.vmimage_arch)
        self.log.info(self.vmimage_provider)

    @fail_on(HTTPError)
    def test_url_versions(self):
        """
        Tests that the version url is reachable
        """
        urlopen(self.vmimage_provider.url_versions).read()

    def test_version(self):
        """
        Tests that the version set is found in by the provider
        """
        self.assertIn(str(self.vmimage_version),
                      [str(v) for v in self.vmimage_provider.get_versions()])


class Image(Base):
    @fail_on(AttributeError)
    def test_get(self):
        vmimage.get(self.vmimage_name, self.vmimage_version,
                    self.vmimage_build, self.vmimage_arch)


class ImageFunctional(Base):
    @fail_on(process.CmdError)
    def test_get(self):
        cmd = 'avocado vmimage get --distro=%s --distro-version=%s --arch=%s'
        cmd %= (self.vmimage_name, self.vmimage_version, self.vmimage_arch)
        process.run(cmd)
