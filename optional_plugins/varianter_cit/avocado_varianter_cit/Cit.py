import logging
import random

from avocado_varianter_cit.CombinationMatrix import CombinationMatrix
from avocado_varianter_cit.Solver import Solver

from avocado.core.output import LOG_UI, Throbber

ITERATIONS_SIZE = 600
LOG = LOG_UI.getChild("Cit")
LOG.setLevel(logging.INFO)


class Cit:

    def __init__(self, input_data, t_value, constraints):
        """
        Creation of CombinationMatrix from user input

        :param input_data: parameters from user
        :param t_value: size of one combination
        :param constraints: constraints of combinations
        """
        self.data = input_data
        self.t_value = t_value
        # CombinationMatrix creation
        self.combination_matrix = CombinationMatrix(input_data, t_value)
        # Creation of solver and simplification of constraints
        self.solver = Solver(input_data, constraints)
        # Combinations which do not match to the constraints are disabled
        self.solver.clean_hash_table(self.combination_matrix, t_value)
        self.final_matrix = []
        self.__throbber = Throbber()

    def final_matrix_init(self):
        """
        Creation of the first solution. This solution is the start of searching
        for the best solution

        :return: solution matrix (list(list))
        """
        self.final_matrix = [self.create_random_row_with_constraints()]
        self.combination_matrix.cover_solution_row(self.final_matrix[0])
        while self.combination_matrix.total_uncovered != 0:
            if self.combination_matrix.total_uncovered < self.combination_matrix.total_covered_more_than_ones:
                new_row = self.compute_row()
            else:
                new_row = self.compute_row_using_hamming_distance()
            self.combination_matrix.cover_solution_row(new_row)
            self.final_matrix.append(new_row)
        return self.final_matrix

    def compute(self):
        """
        Searching for the best solution. It creates one solution and from that,
        it tries to create smaller solution. This searching process is limited
        by ITERATIONS_SIZE. When ITERATIONS_SIZE is 0 the last found solution is
        the best solution.

        :return: The best solution
        """
        self.final_matrix = self.final_matrix_init()
        matrix = [x[:] for x in self.final_matrix]
        iterations = ITERATIONS_SIZE
        step_size = 1
        deleted_rows = []
        while step_size != 0:
            for i in range(step_size):
                delete_row = matrix.pop(random.randint(0, len(matrix) - 1))
                self.combination_matrix.uncover_solution_row(delete_row)
                deleted_rows.append(delete_row)
            LOG.debug("I'm trying solution with size %s and %s iterations",
                      len(matrix), iterations)
            matrix, is_better_solution = self.find_better_solution(iterations, matrix)
            if is_better_solution:
                self.final_matrix = matrix[:]
                deleted_rows = []
                step_size *= 2
                LOG.debug("-----solution with size %s was found-----\n",
                          len(matrix))
                iterations = ITERATIONS_SIZE
            else:
                LOG.debug("-----solution with size %s was not found-----\n",
                          len(matrix))
                for i in range(step_size):
                    self.combination_matrix.cover_solution_row(deleted_rows[i])
                    matrix.append(deleted_rows[i])
                if step_size > 1:
                    step_size = 1
                else:
                    step_size = 0

        return self.final_matrix

    def find_better_solution(self, counter, matrix):
        """
        Changing the matrix to cover all combinations

        :param counter: maximum number of changes in the matrix
        :param matrix: matrix to be changed
        :return: new matrix and is changes have been successful?
        """
        while self.combination_matrix.total_uncovered != 0:
            LOG.debug(self.__throbber.render(), extra={"skip_newline": True})
            solution, row_index, _ = self.use_random_algorithm(matrix)
            if len(solution) != 0:
                self.combination_matrix.uncover_solution_row(matrix[row_index])
                self.combination_matrix.cover_solution_row(solution)
                matrix[row_index] = solution
            if counter == 0:
                return matrix, False
            counter -= 1
        return matrix, True

    def use_random_algorithm(self, matrix):
        """
        Applies one of these algorithms to the matrix.
        It chooses algorithm by random in proportion 1:1:8

        :param matrix: matrix to be changed
        :return: new row of matrix, index of row inside matrix and parameters which has been changed
        """
        switch = random.randint(0, 9)
        if switch == 0:
            solution, row_index, parameters = self.change_one_value(matrix)
        elif switch == 1:
            solution, row_index, parameters = self.change_one_column(matrix)
        else:
            solution, row_index, parameters = self.cover_missing_combination(matrix)
        return solution, row_index, parameters

    def compute_row(self):
        """
        Computation of one row which covers most of combinations

        :return: new solution row
        """
        is_valid_row = False
        while not is_valid_row:
            possible_parameters = list(self.combination_matrix.uncovered_rows)
            row = [-1] * len(self.data)
            while len(possible_parameters) != 0:
                # finding uncovered combination
                combination_parameters_index = random.randint(0, len(possible_parameters) - 1)
                combination_parameters = possible_parameters[combination_parameters_index]
                del possible_parameters[combination_parameters_index]
                combination_row = self.combination_matrix.get_row(combination_parameters)
                possible_combinations = list(combination_row.get_all_uncovered_combinations())
                combination_index = random.randint(0, len(possible_combinations) - 1)
                combination = possible_combinations[combination_index]
                is_parameter_used = False
                # Are parameters already used in row?
                for i in combination_parameters:
                    if row[i] != -1:
                        is_parameter_used = True
                        break
                if is_parameter_used:
                    continue
                row_copy = row.copy()
                # Is combination matches the constraints?
                for index, parameter in enumerate(combination_parameters):
                    row_copy[parameter] = combination[index]
                if self.combination_matrix.is_valid_solution(row_copy):
                    row = row_copy
            # Filling in of free spaces inside the row
            for index, r in enumerate(row):
                if r == -1:
                    is_valid = False
                    while not is_valid:
                        row[index] = random.randint(0, self.data[index] - 1)
                        is_valid = self.combination_matrix.is_valid_solution(row)
            is_valid_row = self.combination_matrix.is_valid_solution(row)

        return row

    def cover_missing_combination(self, matrix):
        """
        Randomly finds one missing combination. This combination puts into each
        row of the matrix. The row with the best coverage is the solution

        :param matrix: matrix to be changed
        :return: solution, index of solution inside matrix and parameters which has been changed
        """
        parameters, combination = self.get_missing_combination_random()
        best_uncover = float("inf")
        best_solution = []
        best_row_index = 0
        for row_index in range(len(matrix)):
            solution = [x for x in matrix[row_index]]
            for index, item in enumerate(parameters):
                solution[item] = combination[index]
            if self.combination_matrix.is_valid_combination(solution, parameters):
                self.combination_matrix.uncover_combination(matrix[row_index], parameters)
                self.combination_matrix.cover_combination(solution, parameters)
                if self.combination_matrix.total_uncovered < best_uncover:
                    best_uncover = self.combination_matrix.total_uncovered
                    best_solution = solution
                    best_row_index = row_index
                self.combination_matrix.uncover_combination(solution, parameters)
                self.combination_matrix.cover_combination(matrix[row_index], parameters)
                if best_uncover == 0:
                    break
        return best_solution, best_row_index, parameters

    def get_missing_combination_random(self):
        """
        Randomly finds one missing combination.

        :return: parameter of combination and values of combination
        """
        possible_parameters = list(self.combination_matrix.uncovered_rows)
        combination_parameters_index = random.randint(0, len(possible_parameters) - 1)
        combination_parameters = possible_parameters[combination_parameters_index]
        combination_row = self.combination_matrix.get_row(combination_parameters)
        possible_combinations = list(combination_row.get_all_uncovered_combinations())
        combination_index = random.randint(0, len(possible_combinations) - 1)
        combination = possible_combinations[combination_index]
        return combination_parameters, combination

    def change_one_column(self, matrix):
        """
        Randomly choose one column of the matrix. In each cell of this column
        changes value. The row with the best coverage is the solution.

        :param matrix: matrix to be changed
        :return: solution, index of solution inside matrix and parameters which has been changed
        """
        column_index = random.randint(0, len(self.data) - 1)
        best_uncover = float("inf")
        best_solution = []
        best_row_index = 0
        for row_index in range(len(matrix)):
            try:
                solution, row_index, parameters = self.change_one_value(matrix, row_index, column_index)
            except ValueError:
                continue
            self.combination_matrix.uncover_combination(matrix[row_index], parameters)
            self.combination_matrix.cover_combination(solution, parameters)
            if self.combination_matrix.total_uncovered < best_uncover:
                best_uncover = self.combination_matrix.total_uncovered
                best_solution = solution
                best_row_index = row_index
            self.combination_matrix.uncover_combination(solution, parameters)
            self.combination_matrix.cover_combination(matrix[row_index], parameters)
            if best_uncover == 0:
                break
        return best_solution, best_row_index, [column_index]

    def change_one_value(self, matrix, row_index=None, column_index=None):
        """
        Change one cell inside the matrix

        :param matrix: matrix to be changed
        :param row_index: row inside matrix. If it's None it is chosen randomly
        :param column_index: column inside matrix. If it's None it is chosen randomly
        :return: solution, index of solution inside matrix and parameters which has been changed
        """
        is_cell_chosen = True
        if row_index is None:
            is_cell_chosen = False
            row_index = random.randint(0, len(matrix) - 1)
        row = [x for x in matrix[row_index]]
        if column_index is None:
            is_cell_chosen = False
            column_index = random.randint(0, len(row) - 1)
        possible_numbers = list(range(0, row[column_index])) + list(
            range(row[column_index] + 1, self.data[column_index]))
        row[column_index] = random.choice(possible_numbers)
        while not self.combination_matrix.is_valid_combination(row, [column_index]):
            possible_numbers.remove(row[column_index])
            if len(possible_numbers) == 0:
                if is_cell_chosen:
                    raise ValueError("Selected cell can't be changed")
                column_index = random.randint(0, len(row) - 1)
                row_index = random.randint(0, len(matrix) - 1)
                row = [x for x in matrix[row_index]]
                possible_numbers = list(range(0, row[column_index])) + list(
                    range(row[column_index] + 1, self.data[column_index]))
            row[column_index] = random.choice(possible_numbers)
        return row, row_index, [column_index]

    def compute_row_using_hamming_distance(self):
        """
        :return: row with the biggest hamming distance from final matrix
        """
        row_1 = self.create_random_row_with_constraints()
        row_2 = self.create_random_row_with_constraints()
        if self.compute_hamming_distance(row_1) >= self.compute_hamming_distance(row_2):
            return row_1
        else:
            return row_2

    def compute_hamming_distance(self, row):
        """
        :return: hamming distance of row from final matrix
        """
        distance = 0
        for final_row in self.final_matrix:
            for index, cell in enumerate(final_row):
                if row[index] != cell:
                    distance += 1
        return distance

    def create_random_row_with_constraints(self):
        """
        Create a new test-case random row, and the row meets the constraints.

        :return: new random row
        :rtype: list
        """
        data_size = len(self.data)
        row = [-1]*data_size

        for parameter in random.sample(range(data_size), data_size):
            possible_values = self.solver.get_possible_values(row, parameter)
            value_choice = random.choice(possible_values)
            row[parameter] = value_choice
        return row
