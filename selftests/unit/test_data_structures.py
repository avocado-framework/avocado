import unittest

from avocado.utils import data_structures


class TestDataStructures(unittest.TestCase):

    """
    Unit tests for avocado.utils.data_structures
    """

    def test_ordered_list_unique(self):
        """
        Verify only unique items are there and the order is kept
        """
        orig = [1, 5, unittest, 1, 3, 'a', 7, 7, None, 0, unittest]
        self.assertEqual(data_structures.ordered_list_unique(orig),
                         [1, 5, unittest, 3, 'a', 7, None, 0])

    def test_geometric_mean(self):
        """
        Verify the correct value is produced and it allows processing of long
        lists of values where some algorithm fails.
        """
        self.assertEqual(data_structures.geometric_mean(xrange(1, 180)),
                         67.1555819421869)

    def test_compare_matrices(self):
        """
        Verify the correct value is produced when comparing matrices.
        """
        # Note that first row contains header in first column, while the
        # second contains only values (for testing purposes)
        matrix1 = [["header", 51.7, 60], [1, 0, 0]]
        matrix2 = [["header", 57.2, 54], [2, 51, 0]]
        self.assertEqual(data_structures.compare_matrices(matrix1, matrix2),
                         ([["header", '+10.6382978723', -10.0], ['+100.0',
                          'error_51/0', '.']], 3, 1, 5))

    def test_lazy_property(self):
        """
        Verify the value is initialized lazily with the correct value
        """
        class DummyClass(object):
            value = False

            @data_structures.LazyProperty
            def dummy_method(self):
                return not self.value

        item = DummyClass()
        self.assertNotIn('dummy_method', item.__dict__)
        self.assertEqual(item.dummy_method, True)
        self.assertIn('dummy_method', item.__dict__)

    def test_callback_register(self):
        """
        Checks CallbackRegister
        """
        class Log(object):
            msgs = []

            def error(self, *args, **kwargs):
                self.msgs.append((args, kwargs))

        def ret_arg(arg):
            return arg

        log = Log()
        register = data_structures.CallbackRegister("MyName", log)
        # Register few correct functions
        register.register(ret_arg, [True], {})
        register.register(ret_arg, [], {"arg": False})
        # Register few incorrect functions (incorrect number of arguments)
        register.register(ret_arg, [True, "incorrect_twice"], {})
        register.register(ret_arg, [True, "incorrect_twice"], {})
        register.register(ret_arg, [True, "incorrect_unique_only"], {}, True)
        # Register incorrect function, which is removed before cleanup
        register.register(ret_arg, [True, "incorrect_removed"], {})
        register.unregister(ret_arg, [True, "incorrect_removed"], {})
        # Run registered functions and check errors were produced accordingly
        register.run()
        self.assertEqual(len(log.msgs), 3)
        self.assertIn("incorrect_unique_only", str(log.msgs[0]))
        self.assertIn("incorrect_twice", str(log.msgs[1]))
        self.assertIn("incorrect_twice", str(log.msgs[2]))


if __name__ == "__main__":
    unittest.main()
