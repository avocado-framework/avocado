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
        self.assertEqual(data_structures.geometric_mean(list(range(1, 180))),
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
                         ([["header", '+10.6383', -10.0],
                           ['+100', 'error_51/0', '.']], 3, 1, 5))

    def test_comma_separated_ranges_to_list(self):
        """
        Verify the correct value is obtained when converting a comma separated
        range string to list
        """
        node_values = ["0", "1-3", "0-1,16-17", "0-1,16-20,23-25"]
        expected_values = [[0], [1, 2, 3], [0, 1, 16, 17],
                           [0, 1, 16, 17, 18, 19, 20, 23, 24, 25]]
        for index, value in enumerate(node_values):
            self.assertEqual(data_structures.comma_separated_ranges_to_list(
                value), expected_values[index])

    def test_lazy_property(self):
        """
        Verify the value is initialized lazily with the correct value
        """
        class DummyClass:
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
        class Log:
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

    def test_time_to_seconds(self):
        self.assertEqual(data_structures.time_to_seconds(None), 0)
        self.assertEqual(data_structures.time_to_seconds("31"), 31)
        self.assertEqual(data_structures.time_to_seconds('10d'), 864000)
        self.assertRaises(ValueError, data_structures.time_to_seconds,
                          "10days")


class TestDataSize(unittest.TestCase):

    def test_valid(self):
        data_structures.DataSize('0')
        data_structures.DataSize('0t')
        data_structures.DataSize('10')

    def test_invalid(self):
        self.assertRaises(data_structures.InvalidDataSize,
                          data_structures.DataSize, 'megabyte')
        self.assertRaises(data_structures.InvalidDataSize,
                          data_structures.DataSize, '-100t')
        self.assertRaises(data_structures.InvalidDataSize,
                          data_structures.DataSize, '0.5g')
        self.assertRaises(data_structures.InvalidDataSize,
                          data_structures.DataSize, '10Mb')

    def test_value_and_type(self):
        self.assertEqual(data_structures.DataSize('0b').b, 0)
        self.assertEqual(data_structures.DataSize('0t').b, 0)

    def test_values(self):
        self.assertEqual(data_structures.DataSize('10m').b, 10485760)
        self.assertEqual(data_structures.DataSize('10M').b, 10485760)


if __name__ == "__main__":
    unittest.main()
