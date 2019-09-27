import unittest

from avocado.core import resolver


class ReferenceResolution(unittest.TestCase):

    """
    Tests on how to initialize and use
    :class:`avocado.core.resolver.ReferenceResolution`
    """

    def test_no_args(self):
        with self.assertRaises(TypeError):
            resolver.ReferenceResolution()

    def test_no_result(self):
        with self.assertRaises(TypeError):
            resolver.ReferenceResolution('/test/reference')

    def test_no_resolutions(self):
        resolution = resolver.ReferenceResolution(
            '/test/reference',
            resolver.ReferenceResolutionResult.NOTFOUND)
        self.assertEqual(len(resolution.resolutions), 0,
                         "Unexpected resolutions found")


if __name__ == '__main__':
    unittest.main()
