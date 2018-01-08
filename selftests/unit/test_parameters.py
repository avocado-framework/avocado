import unittest

from avocado.core import parameters
from avocado.core import tree


class Parameters(unittest.TestCase):

    def test_greedy_path_to_re(self):
        params = parameters.AvocadoParams([tree.TreeNode()],
                                          ['/run'])
        self.assertEqual(params._greedy_path_to_re('').pattern, '^$')
        self.assertEqual(params._greedy_path_to_re('/').pattern, '/$')
        self.assertEqual(params._greedy_path_to_re('/foo/bar').pattern,
                         '/foo/bar$')
        self.assertEqual(params._greedy_path_to_re('foo/bar').pattern,
                         'foo/bar$')
        self.assertEqual(params._greedy_path_to_re('/*/foo').pattern,
                         '/[^/]*/foo$')
        self.assertEqual(params._greedy_path_to_re('foo/*').pattern,
                         'foo/')
        self.assertEqual(params._greedy_path_to_re('/foo/*').pattern,
                         '/foo/')
