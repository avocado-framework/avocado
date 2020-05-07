import random
import unittest
from copy import copy

from avocado_varianter_cit.Cit import Cit
from avocado_varianter_cit.CombinationMatrix import CombinationMatrix
from avocado_varianter_cit.Solver import Solver


class CitInitialization(unittest.TestCase):

    def test_initialization(self):
        parameters = [3, 3, 3, 3]
        constraints = {((0, 0), (2, 0)), ((0, 1), (1, 1), (2, 0)), ((0, 2), (3, 2))}
        t_value = 2
        solver = Solver(parameters, constraints)
        combination_matrix = CombinationMatrix(parameters, t_value)
        solver.clean_hash_table(combination_matrix, t_value)
        cit = Cit(parameters, t_value, constraints)
        self.assertEqual(combination_matrix, cit.combination_matrix, "The initialization of cit algorithm is wrong")


class CitTests(unittest.TestCase):

    def setUp(self):
        parameters = [3, 3, 3, 3]
        constraints = {((0, 0), (2, 0)), ((0, 1), (1, 1), (2, 0)), ((0, 2), (3, 2))}
        t_value = 2
        self.cit = Cit(parameters, t_value, constraints)

    def test_create_random_row_with_constraints(self):
        for _ in range(0, 10):
            row = self.cit.create_random_row_with_constraints()
            with self.subTest(random_row=row):
                self.assertTrue(self.cit.combination_matrix.is_valid_solution(row), "New random row is not valid")

    def test_compute_hamming_distance(self):
        self.cit.final_matrix.append([1, 0, 1, 2])
        self.cit.final_matrix.append([2, 1, 1, 0])
        row = [2, 0, 3, 2]
        expected_distance = 5
        self.assertEqual(expected_distance, self.cit.compute_hamming_distance(row), "Wrong hamming distance")

    def test_final_matrix_init(self):
        combination_matrix = copy(self.cit.combination_matrix)
        final_matrix = self.cit.final_matrix_init()

        expected_total_uncovered = 0
        expected_uncovered_rows = {}
        self.assertEqual(expected_total_uncovered, self.cit.combination_matrix.total_uncovered,
                         "Final matrix don't cover all combinations")
        self.assertEqual(expected_uncovered_rows, self.cit.combination_matrix.uncovered_rows,
                         "Final matrix don't cover all combination rows")

        for row in final_matrix:
            combination_matrix.cover_solution_row(row)
        self.assertEqual(expected_total_uncovered, self.cit.combination_matrix.total_uncovered,
                         "Final matrix don't cover all combinations but CIT thinks it does")
        self.assertEqual(expected_uncovered_rows, self.cit.combination_matrix.uncovered_rows,
                         "Final matrix don't cover all combination rows but CIT thinks it does")

    def test_change_one_value_random(self):
        final_matrix = self.cit.final_matrix_init()
        row, row_index, column_index = self.cit.change_one_value(final_matrix)
        self.assertNotEqual(final_matrix[row_index][column_index[0]], row[column_index[0]], "Value did not change")
        row[column_index[0]] = final_matrix[row_index][column_index[0]]
        self.assertEqual(final_matrix[row_index], row, "Different value was changed")

    def test_change_one_value_with_index(self):
        final_matrix = self.cit.final_matrix_init()
        expected_row_index = 2
        expected_column_index = 0
        function_state = True
        row, row_index, column_index = (None, None, None)
        try:
            row, row_index, column_index = self.cit.change_one_value(final_matrix, row_index=expected_row_index,
                                                                     column_index=expected_column_index)
        except ValueError:
            function_state = False
        if function_state:
            self.assertEqual(expected_column_index, column_index[0], "Column index is wrong")
            self.assertEqual(expected_row_index, row_index, "Row index is wrong")
            self.assertNotEqual(final_matrix[row_index][column_index[0]], row[column_index[0]], "Value did not change")
            row[column_index[0]] = final_matrix[row_index][column_index[0]]
            self.assertEqual(final_matrix[row_index], row, "Different value was changed")
        else:
            self.assertIsNone(row)
            self.assertIsNone(row_index)
            self.assertIsNone(column_index)

    def test_change_one_column(self):
        final_matrix = self.cit.final_matrix_init()
        while self.cit.combination_matrix.total_uncovered == 0:
            delete_row = final_matrix.pop(random.randint(0, len(final_matrix) - 1))
            self.cit.combination_matrix.uncover_solution_row(delete_row)
        expected_total_covered_more_than_ones = self.cit.combination_matrix.total_covered_more_than_ones
        expected_total_uncovered = self.cit.combination_matrix.total_uncovered
        expected_uncovered_rows = copy(self.cit.combination_matrix.uncovered_rows)
        row, row_index, column_index = self.cit.change_one_column(final_matrix)
        self.assertEqual(expected_total_uncovered, self.cit.combination_matrix.total_uncovered, "Coverage was change")
        self.assertEqual(expected_total_covered_more_than_ones,
                         self.cit.combination_matrix.total_covered_more_than_ones,
                         "Coverage was change")
        self.assertEqual(expected_uncovered_rows, self.cit.combination_matrix.uncovered_rows, "Coverage was change")
        self.assertNotEqual(final_matrix[row_index][column_index[0]], row[column_index[0]], "Value did not change")
        row[column_index[0]] = final_matrix[row_index][column_index[0]]
        self.assertEqual(final_matrix[row_index], row, "Different value was changed")

    def test_get_missing_combination_random(self):
        final_matrix = self.cit.final_matrix_init()
        while self.cit.combination_matrix.total_uncovered == 0:
            delete_row = final_matrix.pop(random.randint(0, len(final_matrix) - 1))
            self.cit.combination_matrix.uncover_solution_row(delete_row)
        combination_parameters, combination = self.cit.get_missing_combination_random()
        self.assertEqual(0, self.cit.combination_matrix.hash_table[combination_parameters].hash_table[combination],
                         "Combination is already covered")

    def test_cover_missing_combination(self):
        final_matrix = self.cit.final_matrix_init()
        while self.cit.combination_matrix.total_uncovered == 0:
            delete_row = final_matrix.pop(random.randint(0, len(final_matrix) - 1))
            self.cit.combination_matrix.uncover_solution_row(delete_row)
        expected_total_covered_more_than_ones = self.cit.combination_matrix.total_covered_more_than_ones
        expected_total_uncovered = self.cit.combination_matrix.total_uncovered
        expected_uncovered_rows = copy(self.cit.combination_matrix.uncovered_rows)
        row, row_index, parameters = self.cit.cover_missing_combination(final_matrix)
        self.assertEqual(expected_total_uncovered, self.cit.combination_matrix.total_uncovered, "Coverage was change")
        self.assertEqual(expected_total_covered_more_than_ones,
                         self.cit.combination_matrix.total_covered_more_than_ones,
                         "Coverage was change")
        self.assertEqual(expected_uncovered_rows, self.cit.combination_matrix.uncovered_rows, "Coverage was change")
        self.assertTrue(final_matrix[row_index][parameters[0]] != row[parameters[0]] or
                        final_matrix[row_index][parameters[1]] != row[parameters[1]], "Value did not change")
        row[parameters[0]] = final_matrix[row_index][parameters[0]]
        row[parameters[1]] = final_matrix[row_index][parameters[1]]
        self.assertEqual(final_matrix[row_index], row, "Different value was changed")
