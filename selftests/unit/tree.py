import unittest

from avocado.core import tree


class TreeNode(unittest.TestCase):
    def test_empty(self):
        node = tree.TreeNode()
        self.assertEqual(node.name, "")
        self.assertEqual(node.value, {})
        self.assertEqual(node.children, [])

    def test_parents_child(self):
        child = tree.TreeNode()
        parent = tree.TreeNode(children=[child])
        self.assertIn(child, parent.children)

    def test_childs_parent(self):
        child = tree.TreeNode()
        parent = tree.TreeNode(children=[child])
        self.assertIs(child.parent, parent)

    def test_children_order(self):
        huey = tree.TreeNode(name="Huey")
        dewey = tree.TreeNode(name="Dewey")
        louie = tree.TreeNode(name="Louie")
        scrooge = tree.TreeNode(name="Scrooge", children=[huey, dewey, louie])
        self.assertIs(scrooge.children[0], huey)
        self.assertIs(scrooge.children[1], dewey)
        self.assertIs(scrooge.children[2], louie)

    def test_eq_name(self):
        original = tree.TreeNode(name="same")
        clone = tree.TreeNode(name="same")
        self.assertEqual(original, clone)
        self.assertNotEqual(original, tree.TreeNode(name="other"))

    def test_eq_name_str(self):
        original = tree.TreeNode(name="same")
        self.assertEqual(original, "same")
        self.assertNotEqual(original, "other")

    def test_eq_children(self):
        huey = tree.TreeNode(name="Huey")
        dewey = tree.TreeNode(name="Dewey")
        louie = tree.TreeNode(name="Louie")
        original = tree.TreeNode(children=[huey, dewey, louie])
        clone = tree.TreeNode(children=[huey, dewey, louie])
        self.assertEqual(original, clone)
        self.assertNotEqual(original, tree.TreeNode(children=[huey, dewey]))

    def test_eq_value(self):
        self.assertEqual(
            tree.TreeNode(value={"same": "same"}), tree.TreeNode(value={"same": "same"})
        )
        self.assertNotEqual(
            tree.TreeNode(value={"same": "same"}),
            tree.TreeNode(value={"same": "other"}),
        )

    def test_fingerprint(self):
        self.assertEqual(
            tree.TreeNode("foo").fingerprint(), "/foo{},{},FilterSet([]),FilterSet([])"
        )
        self.assertEqual(
            tree.TreeNode("bar", value={"key": "val"}).fingerprint(),
            "/bar{key: val},{key: /bar},FilterSet([]),FilterSet([])",
        )

    def test_is_leaf(self):
        self.assertTrue(tree.TreeNode().is_leaf)
        self.assertTrue(tree.TreeNode(value={"foo": "bar"}).is_leaf)
        self.assertFalse(tree.TreeNode(children=[tree.TreeNode()]).is_leaf)

    def test_valid_paths(self):
        valid_paths = ["/", "/root", "/root/node"]
        for path in valid_paths:
            try:
                node = tree.TreeNodeEnvOnly(path)
                self.assertEqual(node.path, path)
            except ValueError as e:
                self.fail(f"Unexpected error for path '{path}': {e}")

    def test_environment_loading(self):
        environment = [
            ("/root", "key1", "value1"),
            ("/root/node", "key2", "value2")
        ]
        node = tree.TreeNodeEnvOnly("/root", environment=environment)
        self.assertEqual(node.environment["key1"], "value1")
        self.assertEqual(node.environment.origin["key1"].path, "/root")
        self.assertEqual(node.environment["key2"], "value2")
        self.assertEqual(node.environment.origin["key2"].path, "/root/node")

    def test_invalid_environment_items(self):
        invalid_environment = [
            ("/root", "key1", "value1"),
            ("/root/node", "key2")
        ]
        with self.assertRaises(ValueError):
            tree.TreeNodeEnvOnly("/root", environment=invalid_environment)

    def test_fingerprint_path(self):
        environment = [
            ("/root", "key1", "value1"),
            ("/root/node", "key2", "value2")
        ]
        node = tree.TreeNodeEnvOnly("/root", environment=environment)
        expected_fingerprint = "/root{key1: value1, key2: value2}," \
                               "{key1: /root, key2: /root/node},FilterSet([]),FilterSet([])"
        self.assertEqual(node.fingerprint(), expected_fingerprint)
