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
        orig = [1, 5, unittest, 1, 3, "a", 7, 7, None, 0, unittest]
        self.assertEqual(
            data_structures.ordered_list_unique(orig),
            [1, 5, unittest, 3, "a", 7, None, 0],
        )

    def test_ordered_list_unique_empty(self):
        """
        Test ordered_list_unique with empty list
        """
        self.assertEqual(data_structures.ordered_list_unique([]), [])

    def test_ordered_list_unique_single_item(self):
        """
        Test ordered_list_unique with single item
        """
        self.assertEqual(data_structures.ordered_list_unique([42]), [42])

    def test_ordered_list_unique_all_duplicates(self):
        """
        Test ordered_list_unique with all duplicates
        """
        self.assertEqual(data_structures.ordered_list_unique([1, 1, 1, 1]), [1])

    def test_geometric_mean(self):
        """
        Verify the correct value is produced and it allows processing of long
        lists of values where some algorithm fails.
        """
        self.assertEqual(
            data_structures.geometric_mean(list(range(1, 180))), 67.1555819421869
        )

    def test_geometric_mean_single_value(self):
        """
        Test geometric mean with a single value
        """
        self.assertAlmostEqual(data_structures.geometric_mean([5]), 5.0, places=10)

    def test_geometric_mean_empty_list(self):
        """
        Test geometric mean with empty list
        """
        self.assertIsNone(data_structures.geometric_mean([]))

    def test_geometric_mean_invalid_input(self):
        """
        Test geometric mean with invalid input
        """
        with self.assertRaises(ValueError):
            data_structures.geometric_mean(["invalid", "input"])

    def test_geometric_mean_float_values(self):
        """
        Test geometric mean with float values (note: function converts to int)
        """
        result = data_structures.geometric_mean([1.5, 2.5, 3.5])
        self.assertAlmostEqual(result, 1.8171205928321397, places=5)

    def test_compare_matrices(self):
        """
        Verify the correct value is produced when comparing matrices.
        """
        # Note that first row contains header in first column, while the
        # second contains only values (for testing purposes)
        matrix1 = [["header", 51.7, 60], [1, 0, 0]]
        matrix2 = [["header", 57.2, 54], [2, 51, 0]]
        self.assertEqual(
            data_structures.compare_matrices(matrix1, matrix2),
            ([["header", "+10.6383", -10.0], ["+100", "error_51/0", "."]], 3, 1, 5),
        )

    def test_compare_matrices_empty(self):
        """
        Test compare_matrices with empty matrices
        """
        result = data_structures.compare_matrices([], [])
        self.assertEqual(result, ([], 0, 0, 0))

    def test_compare_matrices_empty_rows(self):
        """
        Test compare_matrices with empty rows
        """
        matrix1 = [[]]
        matrix2 = [[]]
        result = data_structures.compare_matrices(matrix1, matrix2)
        self.assertEqual(result, ([[]], 0, 0, 0))

    def test_compare_matrices_custom_threshold(self):
        """
        Test compare_matrices with custom threshold
        """
        matrix1 = [[100], [200]]
        matrix2 = [[105], [190]]
        result = data_structures.compare_matrices(matrix1, matrix2, threshold=0.1)
        # With 10% threshold, 5% increase should be "same", 5% decrease should be "same"
        self.assertEqual(result[0], [["."], ["."]])
        self.assertEqual(result[3], 2)  # total comparisons

    def test_compare_matrices_zero_handling(self):
        """
        Test compare_matrices zero division handling
        """
        matrix1 = [[0, 5]]
        matrix2 = [[0, 10]]
        result = data_structures.compare_matrices(matrix1, matrix2)
        expected_matrix = [[0, "+100"]]
        self.assertEqual(result[0], expected_matrix)

    def test_comma_separated_ranges_to_list(self):
        """
        Verify the correct value is obtained when converting a comma separated
        range string to list
        """
        node_values = ["0", "1-3", "0-1,16-17", "0-1,16-20,23-25"]
        expected_values = [
            [0],
            [1, 2, 3],
            [0, 1, 16, 17],
            [0, 1, 16, 17, 18, 19, 20, 23, 24, 25],
        ]
        for index, value in enumerate(node_values):
            self.assertEqual(
                data_structures.comma_separated_ranges_to_list(value),
                expected_values[index],
            )

    def test_comma_separated_ranges_single_number(self):
        """
        Test comma_separated_ranges_to_list with single number
        """
        self.assertEqual(data_structures.comma_separated_ranges_to_list("5"), [5])

    def test_comma_separated_ranges_single_range(self):
        """
        Test comma_separated_ranges_to_list with single range
        """
        self.assertEqual(
            data_structures.comma_separated_ranges_to_list("10-12"), [10, 11, 12]
        )

    def test_recursive_compare_dict(self):
        """
        Test recursive_compare_dict with identical dictionaries
        """
        dict1 = {"a": 1, "b": {"c": 2, "d": 3}}
        dict2 = {"a": 1, "b": {"c": 2, "d": 3}}
        result = data_structures.recursive_compare_dict(dict1, dict2)
        self.assertEqual(result, [])

    def test_recursive_compare_dict_different_keys(self):
        """
        Test recursive_compare_dict with different keys
        """
        dict1 = {"a": 1, "b": 2}
        dict2 = {"a": 1, "c": 3}
        result = data_structures.recursive_compare_dict(dict1, dict2)
        self.assertEqual(len(result), 1)
        self.assertIn("DictKey +", result[0])
        self.assertIn("{'b'}", result[0])
        self.assertIn("{'c'}", result[0])

    def test_recursive_compare_dict_different_values(self):
        """
        Test recursive_compare_dict with different values
        """
        dict1 = {"a": 1, "b": 2}
        dict2 = {"a": 1, "b": 3}
        result = data_structures.recursive_compare_dict(dict1, dict2)
        self.assertEqual(len(result), 1)
        self.assertIn("DictKey.b - dict1 value:2, dict2 value:3", result[0])

    def test_recursive_compare_dict_with_lists(self):
        """
        Test recursive_compare_dict with lists
        """
        dict1 = {"a": [1, 2, 3]}
        dict2 = {"a": [1, 2, 4]}
        result = data_structures.recursive_compare_dict(dict1, dict2)
        self.assertEqual(len(result), 1)
        self.assertIn("DictKey.a.3 - dict1 value:3, dict2 value:4", result[0])

    def test_recursive_compare_dict_different_list_lengths(self):
        """
        Test recursive_compare_dict with different list lengths
        """
        dict1 = {"a": [1, 2, 3]}
        dict2 = {"a": [1, 2]}
        result = data_structures.recursive_compare_dict(dict1, dict2)
        self.assertEqual(len(result), 1)
        self.assertIn("DictKey.a + 3 - 2", result[0])

    def test_recursive_compare_dict_mixed_types(self):
        """
        Test recursive_compare_dict with mixed types
        """
        dict1 = {"a": {"b": 1}}
        dict2 = {"a": [1, 2]}
        result = data_structures.recursive_compare_dict(dict1, dict2)
        self.assertEqual(len(result), 1)
        self.assertIn("DictKey.a - dict1 value:", result[0])

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
        self.assertNotIn("dummy_method", item.__dict__)
        self.assertEqual(item.dummy_method, True)
        self.assertIn("dummy_method", item.__dict__)

    def test_lazy_property_class_access(self):
        """
        Test LazyProperty when accessed from class (not instance)
        """

        class DummyClass:
            @data_structures.LazyProperty
            def dummy_method(self):
                return "test"

        # Accessing from class should return None
        self.assertIsNone(DummyClass.dummy_method)

    def test_lazy_property_multiple_instances(self):
        """
        Test LazyProperty with multiple instances
        """

        class DummyClass:
            def __init__(self, value):
                self.value = value

            @data_structures.LazyProperty
            def computed_value(self):
                return self.value * 2

        obj1 = DummyClass(5)
        obj2 = DummyClass(10)

        self.assertEqual(obj1.computed_value, 10)
        self.assertEqual(obj2.computed_value, 20)

        # Verify they're cached independently
        self.assertIn("computed_value", obj1.__dict__)
        self.assertIn("computed_value", obj2.__dict__)

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

    def test_callback_register_once_flag(self):
        """
        Test CallbackRegister with once=True flag
        """

        class Log:
            msgs = []

            def error(self, *args, **kwargs):
                self.msgs.append((args, kwargs))

        def test_func():
            return "test"

        log = Log()
        register = data_structures.CallbackRegister("TestName", log)

        # Register same function multiple times with once=True
        register.register(test_func, [], {}, once=True)
        register.register(test_func, [], {}, once=True)
        register.register(test_func, [], {}, once=True)

        # Should only be registered once
        self.assertEqual(len(register._items), 1)

    def test_callback_register_unregister_nonexistent(self):
        """
        Test CallbackRegister unregister with non-existent item
        """

        class Log:
            msgs = []

            def error(self, *args, **kwargs):
                self.msgs.append((args, kwargs))

        def test_func():
            return "test"

        log = Log()
        register = data_structures.CallbackRegister("TestName", log)

        # Try to unregister something that was never registered
        register.unregister(test_func, [], {})
        # Should not raise an error, just silently do nothing
        self.assertEqual(len(register._items), 0)

    def test_callback_register_empty_run(self):
        """
        Test CallbackRegister run with no registered items
        """

        class Log:
            msgs = []

            def error(self, *args, **kwargs):
                self.msgs.append((args, kwargs))

        log = Log()
        register = data_structures.CallbackRegister("TestName", log)
        register.run()  # Should not raise any error
        self.assertEqual(len(log.msgs), 0)

    def test_time_to_seconds(self):
        self.assertEqual(data_structures.time_to_seconds(None), 0)
        self.assertEqual(data_structures.time_to_seconds("31"), 31)
        self.assertEqual(data_structures.time_to_seconds("10d"), 864000)
        self.assertRaises(ValueError, data_structures.time_to_seconds, "10days")

    def test_time_to_seconds_all_units(self):
        """
        Test time_to_seconds with all supported units
        """
        self.assertEqual(data_structures.time_to_seconds("60s"), 60)
        self.assertEqual(data_structures.time_to_seconds("5m"), 300)
        self.assertEqual(data_structures.time_to_seconds("2h"), 7200)
        self.assertEqual(data_structures.time_to_seconds("1d"), 86400)

    def test_time_to_seconds_case_insensitive(self):
        """
        Test time_to_seconds with uppercase units
        """
        self.assertEqual(data_structures.time_to_seconds("5M"), 300)
        self.assertEqual(data_structures.time_to_seconds("2H"), 7200)
        self.assertEqual(data_structures.time_to_seconds("1D"), 86400)

    def test_time_to_seconds_invalid_formats(self):
        """
        Test time_to_seconds with various invalid formats
        """
        with self.assertRaises(ValueError):
            data_structures.time_to_seconds("invalid")
        with self.assertRaises(ValueError):
            data_structures.time_to_seconds("10x")
        with self.assertRaises(ValueError):
            data_structures.time_to_seconds("10.5h")  # float not supported


class TestBorg(unittest.TestCase):
    """
    Test cases for the Borg pattern implementation
    """

    def test_borg_shared_state(self):
        """
        Test that multiple Borg instances share the same state
        """
        borg1 = data_structures.Borg()
        borg2 = data_structures.Borg()

        # They should be different objects
        self.assertIsNot(borg1, borg2)

        # But they should share the same __dict__
        self.assertIs(borg1.__dict__, borg2.__dict__)

    def test_borg_state_modification(self):
        """
        Test that modifying one Borg instance affects all instances
        """
        borg1 = data_structures.Borg()
        borg2 = data_structures.Borg()

        # Modify state in first instance
        borg1.test_attribute = "test_value"

        # Second instance should see the change
        self.assertEqual(borg2.test_attribute, "test_value")

        # Modify state in second instance
        borg2.another_attribute = 42

        # First instance should see the change
        self.assertEqual(borg1.another_attribute, 42)

    def test_borg_multiple_instances(self):
        """
        Test creating multiple Borg instances and verifying shared state
        """
        instances = [data_structures.Borg() for _ in range(5)]

        # Set an attribute on the first instance
        instances[0].shared_value = "shared"

        # All instances should have the same value
        for instance in instances[1:]:
            self.assertEqual(instance.shared_value, "shared")


class TestDataSize(unittest.TestCase):
    def test_valid(self):
        data_structures.DataSize("0")
        data_structures.DataSize("0t")
        data_structures.DataSize("10")

    def test_invalid(self):
        self.assertRaises(
            data_structures.InvalidDataSize, data_structures.DataSize, "megabyte"
        )
        self.assertRaises(
            data_structures.InvalidDataSize, data_structures.DataSize, "-100t"
        )
        self.assertRaises(
            data_structures.InvalidDataSize, data_structures.DataSize, "10Mb"
        )

    def test_value_and_type(self):
        self.assertEqual(data_structures.DataSize("0b").b, 0)
        self.assertEqual(data_structures.DataSize("0t").b, 0)

    def test_values(self):
        self.assertEqual(data_structures.DataSize("10m").b, 10485760)
        self.assertEqual(data_structures.DataSize("10M").b, 10485760)
        self.assertEqual(data_structures.DataSize("0.5g").b, 536870912)

    def test_all_unit_conversions(self):
        """
        Test all unit conversions (b, k, m, g, t)
        """
        ds = data_structures.DataSize("1024b")
        self.assertEqual(ds.b, 1024)
        self.assertEqual(ds.k, 1)
        self.assertEqual(ds.m, 0)
        self.assertEqual(ds.g, 0)
        self.assertEqual(ds.t, 0)

    def test_kilobyte_conversions(self):
        """
        Test kilobyte unit conversions
        """
        ds = data_structures.DataSize("2k")
        self.assertEqual(ds.b, 2048)
        self.assertEqual(ds.k, 2)
        self.assertEqual(ds.m, 0)

    def test_megabyte_conversions(self):
        """
        Test megabyte unit conversions
        """
        ds = data_structures.DataSize("1m")
        self.assertEqual(ds.b, 1048576)
        self.assertEqual(ds.k, 1024)
        self.assertEqual(ds.m, 1)
        self.assertEqual(ds.g, 0)

    def test_gigabyte_conversions(self):
        """
        Test gigabyte unit conversions
        """
        ds = data_structures.DataSize("1g")
        self.assertEqual(ds.b, 1073741824)
        self.assertEqual(ds.k, 1048576)
        self.assertEqual(ds.m, 1024)
        self.assertEqual(ds.g, 1)
        self.assertEqual(ds.t, 0)

    def test_terabyte_conversions(self):
        """
        Test terabyte unit conversions
        """
        ds = data_structures.DataSize("1t")
        self.assertEqual(ds.b, 1099511627776)
        self.assertEqual(ds.k, 1073741824)
        self.assertEqual(ds.m, 1048576)
        self.assertEqual(ds.g, 1024)
        self.assertEqual(ds.t, 1)

    def test_float_values(self):
        """
        Test DataSize with float values
        """
        ds = data_structures.DataSize("1.5m")
        self.assertEqual(ds.value, 1.5)
        self.assertEqual(ds.unit, "m")
        self.assertEqual(ds.b, 1572864)  # 1.5 * 1048576

    def test_case_insensitive_units(self):
        """
        Test that units are case insensitive
        """
        ds_lower = data_structures.DataSize("10m")
        ds_upper = data_structures.DataSize("10M")
        self.assertEqual(ds_lower.b, ds_upper.b)

    def test_whitespace_handling(self):
        """
        Test DataSize handles whitespace properly
        """
        ds1 = data_structures.DataSize("10m")
        ds2 = data_structures.DataSize("  10m  ")
        ds3 = data_structures.DataSize("10 m")
        self.assertEqual(ds1.b, ds2.b)
        self.assertEqual(ds1.b, ds3.b)

    def test_default_unit_bytes(self):
        """
        Test that default unit is bytes when no unit specified
        """
        ds = data_structures.DataSize("1024")
        self.assertEqual(ds.unit, "b")
        self.assertEqual(ds.value, 1024)
        self.assertEqual(ds.b, 1024)

    def test_zero_values(self):
        """
        Test DataSize with zero values for all units
        """
        for unit in ["b", "k", "m", "g", "t"]:
            ds = data_structures.DataSize(f"0{unit}")
            self.assertEqual(ds.b, 0)
            self.assertEqual(ds.k, 0)
            self.assertEqual(ds.m, 0)
            self.assertEqual(ds.g, 0)
            self.assertEqual(ds.t, 0)

    def test_invalid_formats(self):
        """
        Test various invalid format strings
        """
        invalid_formats = [
            "abc",
            "10x",
            "10MB",  # Wrong case
            "10 GB",  # Wrong case and space
            "",
            "  ",
            "1.2.3m",
            "m10",
        ]

        for invalid_format in invalid_formats:
            with self.subTest(format=invalid_format):
                with self.assertRaises(data_structures.InvalidDataSize):
                    data_structures.DataSize(invalid_format)


if __name__ == "__main__":
    unittest.main()
