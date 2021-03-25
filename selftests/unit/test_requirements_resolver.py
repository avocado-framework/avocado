import unittest

from avocado.core.nrunner import Runnable
from avocado.core.requirements.resolver import RequirementsResolver


class BasicTests(unittest.TestCase):
    """Basic unit tests for the RequirementResolver class"""

    def test_requirements_runnables(self):
        runnable = Runnable(kind='requirement-package', uri=None,
                            requirements=[{'type': 'package', 'name': 'foo'},
                                          {'type': 'package', 'name': 'bar'}])
        requirements_runnables = RequirementsResolver.resolve(runnable)
        kind = 'requirement-package'
        self.assertEqual(kind, requirements_runnables[0].kind)
        self.assertEqual(kind, requirements_runnables[1].kind)
        name0 = 'foo'
        name1 = 'bar'
        self.assertEqual(name0, requirements_runnables[0].kwargs['name'])
        self.assertEqual(name1, requirements_runnables[1].kwargs['name'])
        self.assertIsNone(requirements_runnables[0].kwargs.get('type'))


if __name__ == '__main__':
    unittest.main()
