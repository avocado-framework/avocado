import unittest

from avocado.core import parameters, tree


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

    def test_same_origin_of_different_nodes(self):
        # ideally we have one tree, therefor shared key
        # have identical origin (id of the origin env)
        foo = tree.TreeNode().get_node("/foo", True)
        root = foo.parent
        root.value = {'timeout': 1}
        bar = root.get_node("/bar", True)
        params1 = parameters.AvocadoParams([foo, bar], '/')
        self.assertEqual(params1.get('timeout'), 1)
        self.assertEqual(params1.get('timeout', '/foo/'), 1)
        self.assertEqual(params1.get('timeout', '/bar/'), 1)
        # Sometimes we get multiple trees, but if they claim the origin
        # is of the same path, let's trust it (even when the values
        # differ)
        # note: This is an artificial example which should not happen
        # in production. Anyway in json-variants-loader we do create
        # only leave-nodes without connecting the parents, which result
        # in same paths with different node objects. Let's make sure
        # they behave correctly.
        baz = tree.TreeNode().get_node("/baz", True)
        baz.parent.value = {'timeout': 2}
        params2 = parameters.AvocadoParams([foo, baz], '/')
        self.assertEqual(params2.get('timeout'), 1)
        self.assertEqual(params2.get('timeout', '/foo/'), 1)
        self.assertEqual(params2.get('timeout', '/baz/'), 2)
        # Note: Different origin of the same value, which should produce
        # a crash, are tested in yaml2mux selftest


if __name__ == '__main__':
    unittest.main()
