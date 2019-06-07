import unittest

from avocado_varianter_cit.CombinationMatrix import CombinationMatrix
from avocado_varianter_cit.CombinationRow import CombinationRow


def combination_row_equals(row_1, row_2):
    return (row_1.covered_more_than_ones == row_2.covered_more_than_ones and row_1.uncovered == row_2.uncovered
            and row_1.hash_table == row_2.hash_table)


class MatrixInitialization(unittest.TestCase):

    def test_combination_matrix_initialization(self):
        """
        Test of proper initialization
        """
        data = [3, 3, 3, 4]
        t_value = 2
        matrix = CombinationMatrix(data, t_value)
        excepted_uncovered = 63
        excepted_covered_more_than_ones = 0
        excepted_row_size = 6
        excepted_hash_table = {(0, 1): CombinationRow(data, t_value, (0, 1)),
                               (0, 2): CombinationRow(data, t_value, (0, 2)),
                               (0, 3): CombinationRow(data, t_value, (0, 3)),
                               (1, 2): CombinationRow(data, t_value, (1, 2)),
                               (1, 3): CombinationRow(data, t_value, (1, 3)),
                               (2, 3): CombinationRow(data, t_value, (2, 3))}
        self.assertEqual(matrix.total_uncovered, excepted_uncovered, "Total uncovered number is wrong.")
        self.assertEqual(matrix.total_covered_more_than_ones, excepted_covered_more_than_ones,
                         "Total uovered_more_than_ones number is wrong.")
        self.assertEqual(len(matrix.hash_table), excepted_row_size, "Matrix has wrong row size")
        self.assertEqual(len(matrix.uncovered_rows), excepted_row_size, "Matrix has wrong uncovered row size")
        for key in matrix.hash_table:
            with self.subTest(combination=key):
                self.assertTrue(combination_row_equals(matrix.hash_table[key], excepted_hash_table[key]))


class CombinationMatrixTest(unittest.TestCase):

    def setUp(self):
        self.data = [3, 3, 3, 4]
        self.t_value = 2
        self.matrix = CombinationMatrix(self.data, self.t_value)
        self.excepted_hash_table = {(0, 1): CombinationRow(self.data, self.t_value, (0, 1)),
                                    (0, 2): CombinationRow(self.data, self.t_value, (0, 2)),
                                    (0, 3): CombinationRow(self.data, self.t_value, (0, 3)),
                                    (1, 2): CombinationRow(self.data, self.t_value, (1, 2)),
                                    (1, 3): CombinationRow(self.data, self.t_value, (1, 3)),
                                    (2, 3): CombinationRow(self.data, self.t_value, (2, 3))}

    def test_cover_solution_row(self):
        solution_row = [1, 0, 2, 3]
        excepted_uncovered = 57
        excepted_covered_more_than_ones = 0
        excepted_uncovered_row_size = 6
        self.excepted_hash_table[0, 1].cover_cell((1, 0))
        self.excepted_hash_table[0, 2].cover_cell((1, 2))
        self.excepted_hash_table[0, 3].cover_cell((1, 3))
        self.excepted_hash_table[1, 2].cover_cell((0, 2))
        self.excepted_hash_table[1, 3].cover_cell((0, 3))
        self.excepted_hash_table[2, 3].cover_cell((2, 3))
        self.matrix.cover_solution_row(solution_row)
        self.assertEqual(excepted_uncovered, self.matrix.total_uncovered, "Total uncovered number is wrong.")
        self.assertEqual(excepted_covered_more_than_ones, self.matrix.total_covered_more_than_ones,
                         "Total uovered_more_than_ones number is wrong.")
        self.assertEqual(excepted_uncovered_row_size, len(self.matrix.uncovered_rows),
                         "Matrix has wrong uncovered row size")
        for key in self.matrix.hash_table:
            with self.subTest(combination=key):
                self.assertTrue(combination_row_equals(self.matrix.hash_table[key], self.excepted_hash_table[key]))
        solution_row = [0, 0, 2, 3]
        self.matrix.cover_solution_row(solution_row)
        solution_row = [0, 1, 2, 3]
        self.matrix.cover_solution_row(solution_row)
        solution_row = [0, 2, 2, 3]
        self.matrix.cover_solution_row(solution_row)
        solution_row = [1, 1, 2, 3]
        self.matrix.cover_solution_row(solution_row)
        solution_row = [1, 2, 2, 3]
        self.matrix.cover_solution_row(solution_row)
        solution_row = [2, 0, 2, 3]
        self.matrix.cover_solution_row(solution_row)
        solution_row = [2, 1, 2, 3]
        self.matrix.cover_solution_row(solution_row)
        solution_row = [2, 2, 2, 3]
        self.matrix.cover_solution_row(solution_row)
        excepted_uncovered_row_size = 5
        excepted_uncovered = 41
        excepted_covered_more_than_ones = 13
        self.assertEqual(excepted_uncovered, self.matrix.total_uncovered, "Total uncovered number is wrong.")
        self.assertEqual(excepted_covered_more_than_ones, self.matrix.total_covered_more_than_ones,
                         "Total uovered_more_than_ones number is wrong.")
        self.assertEqual(excepted_uncovered_row_size, len(self.matrix.uncovered_rows),
                         "Matrix has wrong uncovered row size")

    def test_cover_combination(self):
        solution_row = [1, 0, 2, 3]
        self.matrix.cover_combination(solution_row, (1, 0))
        excepted_uncovered_row_size = 6
        excepted_uncovered = 58
        excepted_covered_more_than_ones = 0
        self.excepted_hash_table[0, 1].cover_cell((1, 0))
        self.excepted_hash_table[0, 2].cover_cell((1, 2))
        self.excepted_hash_table[0, 3].cover_cell((1, 3))
        self.excepted_hash_table[1, 2].cover_cell((0, 2))
        self.excepted_hash_table[1, 3].cover_cell((0, 3))
        self.assertEqual(excepted_uncovered, self.matrix.total_uncovered, "Total uncovered number is wrong.")
        self.assertEqual(excepted_covered_more_than_ones, self.matrix.total_covered_more_than_ones,
                         "Total uovered_more_than_ones number is wrong.")
        self.assertEqual(excepted_uncovered_row_size, len(self.matrix.uncovered_rows),
                         "Matrix has wrong uncovered row size")
        for key in self.matrix.hash_table:
            with self.subTest(combination=key):
                self.assertTrue(combination_row_equals(self.matrix.hash_table[key], self.excepted_hash_table[key]))

        self.matrix.cover_combination(solution_row, (1, 0))
        excepted_covered_more_than_ones = 5
        self.assertEqual(excepted_uncovered, self.matrix.total_uncovered, "Total uncovered number is wrong.")
        self.assertEqual(excepted_covered_more_than_ones, self.matrix.total_covered_more_than_ones,
                         "Total uovered_more_than_ones number is wrong.")
        self.assertEqual(excepted_uncovered_row_size, len(self.matrix.uncovered_rows),
                         "Matrix has wrong uncovered row size")

    def test_uncover_solution_row(self):
        solution_row = [1, 0, 2, 3]
        self.matrix.cover_solution_row(solution_row)
        self.matrix.uncover_solution_row(solution_row)
        excepted_uncovered_row_size = 6
        excepted_uncovered = 63
        excepted_covered_more_than_ones = 0
        self.assertEqual(excepted_uncovered, self.matrix.total_uncovered, "Total uncovered number is wrong.")
        self.assertEqual(excepted_covered_more_than_ones, self.matrix.total_covered_more_than_ones,
                         "Total uovered_more_than_ones number is wrong.")
        self.assertEqual(excepted_uncovered_row_size, len(self.matrix.uncovered_rows),
                         "Matrix has wrong uncovered row size")
        for key in self.matrix.hash_table:
            with self.subTest(combination=key):
                self.assertTrue(combination_row_equals(self.matrix.hash_table[key], self.excepted_hash_table[key]))

        self.matrix.cover_solution_row(solution_row)
        self.matrix.cover_solution_row(solution_row)
        self.excepted_hash_table[0, 1].cover_cell((1, 0))
        self.excepted_hash_table[0, 2].cover_cell((1, 2))
        self.excepted_hash_table[0, 3].cover_cell((1, 3))
        self.excepted_hash_table[1, 2].cover_cell((0, 2))
        self.excepted_hash_table[1, 3].cover_cell((0, 3))
        self.excepted_hash_table[2, 3].cover_cell((2, 3))
        self.matrix.uncover_solution_row(solution_row)
        excepted_uncovered_row_size = 6
        excepted_uncovered = 57
        excepted_covered_more_than_ones = 0
        self.assertEqual(excepted_uncovered, self.matrix.total_uncovered, "Total uncovered number is wrong.")
        self.assertEqual(excepted_covered_more_than_ones, self.matrix.total_covered_more_than_ones,
                         "Total uovered_more_than_ones number is wrong.")
        self.assertEqual(excepted_uncovered_row_size, len(self.matrix.uncovered_rows),
                         "Matrix has wrong uncovered row size")
        for key in self.matrix.hash_table:
            with self.subTest(combination=key):
                self.assertTrue(combination_row_equals(self.matrix.hash_table[key], self.excepted_hash_table[key]))

    def test_uncover_combination(self):
        solution_row = [1, 0, 2, 3]
        self.matrix.cover_solution_row(solution_row)
        excepted_uncovered_row_size = 6
        excepted_uncovered = 62
        excepted_covered_more_than_ones = 0
        self.excepted_hash_table[2, 3].cover_cell((2, 3))
        self.matrix.uncover_combination(solution_row, (0, 1))
        self.assertEqual(excepted_uncovered, self.matrix.total_uncovered, "Total uncovered number is wrong.")
        self.assertEqual(excepted_covered_more_than_ones, self.matrix.total_covered_more_than_ones,
                         "Total uovered_more_than_ones number is wrong.")
        self.assertEqual(excepted_uncovered_row_size, len(self.matrix.uncovered_rows),
                         "Matrix has wrong uncovered row size")
        for key in self.matrix.hash_table:
            with self.subTest(combination=key):
                self.assertTrue(combination_row_equals(self.matrix.hash_table[key], self.excepted_hash_table[key]))

    def test_uncover(self):
        solution_row = [1, 0, 2, 3]
        self.matrix.cover_solution_row(solution_row)
        self.matrix.cover_solution_row(solution_row)
        excepted_uncovered_row_size = 6
        excepted_uncovered = 63
        excepted_covered_more_than_ones = 0
        self.matrix.uncover()
        self.assertEqual(excepted_uncovered, self.matrix.total_uncovered, "Total uncovered number is wrong.")
        self.assertEqual(excepted_covered_more_than_ones, self.matrix.total_covered_more_than_ones,
                         "Total uovered_more_than_ones number is wrong.")
        self.assertEqual(excepted_uncovered_row_size, len(self.matrix.uncovered_rows),
                         "Matrix has wrong uncovered row size")
        for key in self.matrix.hash_table:
            with self.subTest(combination=key):
                self.assertTrue(combination_row_equals(self.matrix.hash_table[key], self.excepted_hash_table[key]))
