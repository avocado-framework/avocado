
from avocado import Test
from avocado.utils import vmimage


class GPL2(Test):
    """
    Example test using docstring requirements.

    :avocado: requirement={"type": "file", "name": "gpl-2.0.txt", "locations": "https://mirrors.kernel.org/gnu/Licenses/gpl-2.0.txt", "asset_hash": "4cc77b90af91e615a64ae04893fdffa7939db84c"}
    """

    def setUp(self):
        # To make testing easy, lets fetch a small assets into `by_name`.
        location = 'https://mirrors.kernel.org/gnu/Licenses/'
        gpl2 = 'gpl-2.0.txt'
        gpl2_location = "%s%s" % (location, gpl2)
        self.gpl2 = self.fetch_asset(
            name=gpl2,
            asset_hash='4cc77b90af91e615a64ae04893fdffa7939db84c',
            locations=gpl2_location,
            find_only=True,
            cancel_on_missing=True)

    def test_find_gpl(self):
        self.assertIsInstance(self.gpl2, str)


class GPL3(Test):
    """
    Example test using docstring requirements.

    :avocado: requirement={"type": "file", "name": "gpl-3.0.txt", "locations": "https://mirrors.kernel.org/gnu/Licenses/gpl-3.0.txt", "asset_hash": "31a3d460bb3c7d98845187c716a30db81c44b615"}
    """

    def setUp(self):
        # To make testing easy, lets fetch a small assets into `by_name`.
        location = 'https://mirrors.kernel.org/gnu/Licenses/'
        gpl3 = 'gpl-3.0.txt'
        gpl3_location = "%s%s" % (location, gpl3)
        self.gpl3 = self.fetch_asset(
            name=gpl3,
            asset_hash='31a3d460bb3c7d98845187c716a30db81c44b615',
            locations=gpl3_location,
            find_only=True,
            cancel_on_missing=True)

    def test_find_gpl(self):
        self.assertIsInstance(self.gpl3, str)


class LGPL2(Test):
    """
    Example test using docstring requirements.

    :avocado: requirement={"type": "file", "name": "lgpl-2.0.txt", "locations": "https://mirrors.kernel.org/gnu/Licenses/lgpl-2.0.txt", "asset_hash": "ba8966e2473a9969bdcab3dc82274c817cfd98a1"}
    :avocado: requirement={"type": "file", "name": "lgpl-2.1.txt", "locations": "https://mirrors.kernel.org/gnu/Licenses/lgpl-2.1.txt", "asset_hash": "01a6b4bf79aca9b556822601186afab86e8c4fbf"}
    """

    def setUp(self):
        # To make testing easy, lets fetch a small assets into `by_name`.
        location = 'https://mirrors.kernel.org/gnu/Licenses/'
        lgpl2 = 'lgpl-2.0.txt'
        lgpl2_1 = 'lgpl-2.1.txt'
        lgpl2_location = "%s%s" % (location, lgpl2)
        lgpl2_1_location = "%s%s" % (location, lgpl2_1)
        self.lgpl2 = self.fetch_asset(
            name=lgpl2,
            asset_hash='ba8966e2473a9969bdcab3dc82274c817cfd98a1',
            locations=lgpl2_location,
            find_only=True,
            cancel_on_missing=True)
        self.lgpl2_1 = self.fetch_asset(
            name=lgpl2_1,
            asset_hash='01a6b4bf79aca9b556822601186afab86e8c4fbf',
            locations=lgpl2_1_location,
            find_only=True,
            cancel_on_missing=True)

    def test_find_lgpl2(self):
        self.assertIsInstance(self.lgpl2, str)

    def test_find_lgpl2_1(self):
        self.assertIsInstance(self.lgpl2_1, str)


class Vmimage(Test):
    """
    Example test using docstring requirements.

    :avocado: requirement={"type": "image", "name": "cirros", "version": "0.5.0", "arch": "x86_64"}
    """

    def setUp(self):
        # To make testing easy, lets download a small image (16MB).
        self.image = vmimage.get(
            'cirros', arch='x86_64', version='0.5.0',
            cache_dir=self.cache_dirs[0]
        )

    def test_find_image(self):
        self.assertIsInstance(self.image, vmimage.Image)
