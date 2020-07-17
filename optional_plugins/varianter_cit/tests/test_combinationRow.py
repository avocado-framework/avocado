import unittest

from avocado_varianter_cit.CombinationRow import CombinationRow


class RowInitialization(unittest.TestCase):

    def test_combination_row_initialization(self):
        """
        Test of proper initialization
        """
        data = [3, 3, 3, 4]
        parameters = (1, 3)
        t_value = 2
        row = CombinationRow(data, t_value, parameters)
        excepted_uncovered = 12
        excepted_covered_more_than_ones = 0
        excepted_hash_table = {(0, 0): 0, (0, 1): 0, (0, 2): 0, (0, 3): 0,
                               (1, 0): 0, (1, 1): 0, (1, 2): 0, (1, 3): 0,
                               (2, 0): 0, (2, 1): 0, (2, 2): 0, (2, 3): 0}
        self.assertEqual(row.uncovered, excepted_uncovered, "Uncovered number is wrong.")
        self.assertEqual(row.covered_more_than_ones, excepted_covered_more_than_ones,
                         "Covered_more_than_ones number is wrong.")
        self.assertEqual(row.hash_table, excepted_hash_table, "Hash table is wrong.")


class CombinationRowTest(unittest.TestCase):

    def setUp(self):
        self.data = [3, 3, 3, 4]
        self.parameters = (1, 3)
        self.t_value = 2
        self.row = CombinationRow(self.data, self.t_value, self.parameters)

    # Tests of cover_cell function

    def test_cover_cell_uncovered_value(self):
        self.assertEqual(self.row.cover_cell((0, 0)), (-1, 0), "cover_cell return wrong values")
        self.assertEqual(self.row.uncovered, 11, "cover_cell create wrong uncovered value")
        self.assertEqual(self.row.covered_more_than_ones, 0, "cover_cell create wrong covered_more_than_ones value")
        self.assertEqual(self.row.hash_table[(0, 0)], 1, "cover_cell don't cover values")

    def test_cover_cell_covered_value(self):
        self.row.hash_table[(0, 0)] = 1
        self.row.uncovered = 11
        self.assertEqual(self.row.cover_cell((0, 0)), (0, 1), "cover_cell return wrong values")
        self.assertEqual(self.row.uncovered, 11, "cover_cell create wrong uncovered value")
        self.assertEqual(self.row.covered_more_than_ones, 1, "cover_cell create wrong covered_more_than_ones value")
        self.assertEqual(self.row.hash_table[(0, 0)], 2, "cover_cell don't cover values")

    def test_cover_cell_cover_disabled_value(self):
        self.row.hash_table[(0, 0)] = None
        self.assertEqual(self.row.cover_cell((0, 0)), (0, 0), "cover_cell return wrong values")
        self.assertEqual(self.row.uncovered, 12, "cover_cell create wrong uncovered value")
        self.assertEqual(self.row.covered_more_than_ones, 0, "cover_cell create wrong covered_more_than_ones value")
        self.assertEqual(self.row.hash_table[(0, 0)], None, "cover_cell change disabled value")

    # Tests of uncover_cell function

    def test_uncover_cell_uncovered_value(self):
        self.assertEqual(self.row.uncover_cell((0, 0)), (0, 0), "uncover_cell return wrong values")
        self.assertEqual(self.row.uncovered, 12, "uncover_cell create wrong uncovered value")
        self.assertEqual(self.row.covered_more_than_ones, 0, "uncover_cell create wrong covered_more_than_ones value")
        self.assertEqual(self.row.hash_table[(0, 0)], 0, "uncover_cell change uncovered value")

    def test_uncover_cell_covered_value(self):
        self.row.hash_table[(0, 0)] = 1
        self.row.uncovered = 11
        self.assertEqual(self.row.uncover_cell((0, 0)), (1, 0), "uncover_cell return wrong values")
        self.assertEqual(self.row.uncovered, 12, "uncover_cell create wrong uncovered value")
        self.assertEqual(self.row.covered_more_than_ones, 0, "uncover_cell create wrong covered_more_than_ones value")
        self.assertEqual(self.row.hash_table[(0, 0)], 0, "uncover_cell change uncovered value")

    def test_uncover_cell_covered_more_than_one_value(self):
        self.row.hash_table[(0, 0)] = 2
        self.row.uncovered = 11
        self.row.covered_more_than_ones = 1
        self.assertEqual(self.row.uncover_cell((0, 0)), (0, -1), "uncover_cell return wrong values")
        self.assertEqual(self.row.uncovered, 11, "uncover_cell create wrong uncovered value")
        self.assertEqual(self.row.covered_more_than_ones, 0, "uncover_cell create wrong covered_more_than_ones value")
        self.assertEqual(self.row.hash_table[(0, 0)], 1, "uncover_cell change uncovered value")

    def test_uncover_cell_disabled_value(self):
        self.row.hash_table[(0, 0)] = None
        self.assertEqual(self.row.uncover_cell((0, 0)), (0, 0), "uncover_cell return wrong values")
        self.assertEqual(self.row.uncovered, 12, "uncover_cell create wrong uncovered value")
        self.assertEqual(self.row.covered_more_than_ones, 0, "uncover_cell create wrong covered_more_than_ones value")
        self.assertEqual(self.row.hash_table[(0, 0)], None, "uncover_cell change disabled value")

    # Test of completely_uncover function

    def test_completely_uncover(self):
        self.row.hash_table[(0, 0)] = 1
        self.row.hash_table[(0, 1)] = 2
        self.row.hash_table[(0, 2)] = None
        self.row.completely_uncover()
        self.assertEqual(self.row.uncovered, 11, "completely_uncover create wrong uncovered value")
        self.assertEqual(self.row.covered_more_than_ones, 0,
                         "completely_uncover create wrong covered_more_than_ones value")
        self.assertEqual(self.row.hash_table[(0, 0)], 0, "completely_uncover don't uncover value")
        self.assertEqual(self.row.hash_table[(0, 1)], 0, "completely_uncover don't uncover value")
        self.assertEqual(self.row.hash_table[(0, 2)], None, "completely_uncover change disabled value")

    # Tests of del_cell function

    def test_del_cell_uncovered_value(self):
        self.assertEqual(self.row.del_cell((0, 0)), -1, "del_cell return wrong values")
        self.assertEqual(self.row.uncovered, 11, "del_cell create wrong uncovered value")
        self.assertEqual(self.row.covered_more_than_ones, 0, "del_cell create wrong covered_more_than_ones value")
        self.assertEqual(self.row.hash_table[(0, 0)], None, "del_cell don't disable value")

    def test_del_cell_disabled_value(self):
        self.row.hash_table[(0, 0)] = None
        self.row.uncovered = 11
        self.assertEqual(self.row.del_cell((0, 0)), 0, "del_cell return wrong values")
        self.assertEqual(self.row.uncovered, 11, "del_cell create wrong uncovered value")
        self.assertEqual(self.row.covered_more_than_ones, 0, "del_cell create wrong covered_more_than_ones value")
        self.assertEqual(self.row.hash_table[(0, 0)], None, "del_cell don't disable value")

    # Tests of is_valid function

    def test_is_valid_valid(self):
        self.assertEqual(self.row.is_valid((0, 0)), True, "is_valid return wrong values")

    def test_is_valid_invalid(self):
        self.row.hash_table[(0, 0)] = None
        self.assertEqual(self.row.is_valid((0, 0)), False, "is_valid return wrong values")

    # Test of get_all_uncovered_combinations function

    def test_get_all_uncovered_combinations(self):
        self.row.hash_table[(0, 0)] = None
        self.row.hash_table[(0, 1)] = 1
        self.row.hash_table[(0, 2)] = 2
        self.row.hash_table[(0, 3)] = 3
        ex = [(1, 0), (1, 1), (1, 2), (1, 3),
              (2, 0), (2, 1), (2, 2), (2, 3)]
        self.assertEqual(len(set(self.row.get_all_uncovered_combinations()).intersection(ex)), len(ex))


if __name__ == '__main__':
    unittest.main()
