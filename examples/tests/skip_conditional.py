from avocado import Test, skipIf, skipUnless


class BaseTest(Test):
    """Base class for tests

    :avocado: disable
    """

    SUPPORTED_ENVS = []

    @skipUnless(lambda x: 'BARE_METAL' in x.SUPPORTED_ENVS,
                'Bare metal environment is required')
    def test_bare_metal(self):
        pass

    @skipIf(lambda x: getattr(x, 'MEMORY', 0) < 4096,
            'Not enough memory for test')
    def test_large_memory(self):
        pass

    @skipUnless(lambda x: 'VIRTUAL_MACHINE' in x.SUPPORTED_ENVS,
                'Virtual Machine environment is required')
    def test_nested_virtualization(self):
        pass

    @skipUnless(lambda x: 'CONTAINER' in x.SUPPORTED_ENVS,
                'Container environment is required')
    def test_container(self):
        pass


class BareMetal(BaseTest):

    SUPPORTED_ENVS = ['BARE_METAL']
    MEMORY = 2048

    def test_specific(self):
        pass


class NonBareMetal(BaseTest):

    SUPPORTED_ENVS = ['VIRTUAL_MACHINE', 'CONTAINER']

    def test_specific(self):
        pass
