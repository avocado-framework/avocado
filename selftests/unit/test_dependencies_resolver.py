import unittest

from avocado.core.nrunner.runnable import Runnable
from avocado.plugins.dependency import DependencyResolver


class BasicTests(unittest.TestCase):
    """Basic unit tests for the DependencyResolver class"""

    def test_dependencies_runnables(self):
        runnable = Runnable(
            kind="package",
            uri=None,
            dependencies=[
                {"type": "package", "name": "foo"},
                {"type": "package", "name": "bar"},
            ],
        )
        dependency_runnables = DependencyResolver.pre_test_runnables(runnable)
        kind = "package"
        self.assertEqual(kind, dependency_runnables[0].kind)
        self.assertEqual(kind, dependency_runnables[1].kind)
        name0 = "foo"
        name1 = "bar"
        self.assertEqual(name0, dependency_runnables[0].kwargs["name"])
        self.assertEqual(name1, dependency_runnables[1].kwargs["name"])
        self.assertIsNone(dependency_runnables[0].kwargs.get("type"))


if __name__ == "__main__":
    unittest.main()
