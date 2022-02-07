import itertools

from .CombinationRow import CombinationRow as Row


class CombinationMatrix:
    """
    CombinationMatrix object stores Rows of combinations into dictionary.
    And also stores which rows are not covered. Keys in dictionary are parameters
    of combinations and values are CombinationRow objects. CombinationMatrix object
    has information about how many combinations are uncovered and how many of them
    are covered more than ones.
    """

    def __init__(self, input_data, t_value):
        """
        :param input_data: list of data from user
        :param t_value: t number from user
        """
        self.hash_table = {}
        self.uncovered_rows = {}
        self.total_uncovered = 0
        self.total_covered_more_than_ones = 0
        # Creation of rows
        for c in itertools.combinations(range(len(input_data)), t_value):
            row = Row(input_data, t_value, c)
            self.total_uncovered += row.uncovered
            self.hash_table[c] = row
            self.uncovered_rows[c] = c

    def cover_solution_row(self, row):
        """
        Cover all combination by one row from possible solution

        :param row: one row from solution
        :return: number of still uncovered combinations
        """
        for key, value in self.hash_table.items():
            val = []
            # Getting combination from solution
            for i in key:
                val.append(row[i])

            uncovered_difference, covered_more_than_ones_difference = value.cover_cell(val)
            # Deleting covered row from uncovered rows
            if value.uncovered == 0:
                self.uncovered_rows.pop(key, None)
            self.total_uncovered += uncovered_difference
            self.total_covered_more_than_ones += covered_more_than_ones_difference

        return self.total_uncovered

    def cover_combination(self, row, parameters):
        """
        Cover combination of specific parameters by one row from possible solution

        :param row: one row from solution
        :param parameters: parameters which has to be covered
        :return: number of still uncovered combinations
        """
        for key, value in self.hash_table.items():
            for parameter in parameters:
                if parameter in key:
                    val = []
                    # Getting combination from solution
                    for i in key:
                        val.append(row[i])

                    uncovered_difference, covered_more_than_ones_difference = value.cover_cell(val)
                    # Deleting covered row from uncovered rows
                    if value.uncovered == 0:
                        self.uncovered_rows.pop(key, None)
                    self.total_uncovered += uncovered_difference
                    self.total_covered_more_than_ones += covered_more_than_ones_difference
                    break
        return self.total_uncovered

    def uncover_solution_row(self, row):
        """
        Uncover all combination by one row from possible solution

        :param row: one row from solution
        :return: number of uncovered combinations
        """
        for key, value in self.hash_table.items():
            val = []
            # Getting combination from solution
            for i in key:
                val.append(row[i])

            uncovered_difference, covered_more_than_ones_difference = value.uncover_cell(val)
            # Adding uncovered row to uncovered rows
            if value.uncovered != 0:
                self.uncovered_rows[key] = key
            self.total_uncovered += uncovered_difference
            self.total_covered_more_than_ones += covered_more_than_ones_difference

        return self.total_uncovered

    def uncover_combination(self, row, parameters):
        """
        Uncover combination of specific parameters by one row from possible solution

        :param row: one row from solution
        :param parameters: parameters which has to be covered
        :return: number of uncovered combinations
        """
        for key, value in self.hash_table.items():
            for parameter in parameters:
                if parameter in key:
                    val = []
                    # Getting combination from solution
                    for i in key:
                        val.append(row[i])

                    uncovered_difference, covered_more_than_ones_difference = value.uncover_cell(val)
                    # Adding uncovered row to uncovered rows
                    if value.uncovered != 0:
                        self.uncovered_rows[key] = key
                    self.total_uncovered += uncovered_difference
                    self.total_covered_more_than_ones += covered_more_than_ones_difference
                    break
        return self.total_uncovered

    def uncover(self):
        """
        Uncover all combinations
        """
        self.total_covered_more_than_ones = 0
        self.total_uncovered = 0
        for _, value in self.hash_table.items():
            value.completely_uncover()
            self.total_uncovered += value.uncovered

    def is_valid_solution(self, row):
        """
        Is the solution row match the constraints.

        :param row: one row from solution
        """
        for key, value in self.hash_table.items():
            val = []
            for i in key:
                val.append(row[i])

            if not value.is_valid(val):
                return False

        return True

    def is_valid_combination(self, row, parameters):
        """
        Is the specific parameters from solution row match the constraints.

        :param row: one row from solution
        :param parameters: parameters from row
        """
        for key, value in self.hash_table.items():
            for parameter in parameters:
                if parameter in key:
                    val = []
                    for i in key:
                        val.append(row[i])

                    if not value.is_valid(val):
                        return False
                    break
        return True

    def del_cell(self, parameters, combination):
        """
        Disable one combination. If combination is disabled it means that
        the combination does not match the constraints

        :param parameters: parameters whose combination is disabled
        :param combination: combination to be disabled
        """
        row = self.hash_table[tuple(parameters)]
        uncovered_difference = row.del_cell(combination)
        if row.uncovered == 0:
            self.uncovered_rows.pop(tuple(parameters), None)
        self.total_uncovered += uncovered_difference

    def get_row(self, key):
        """
        :param key: identifier of row
        :return: CombinationRow
        """
        return self.hash_table[tuple(key)]

    def __eq__(self, other):
        return (self.total_uncovered == other.total_uncovered and
                self.total_covered_more_than_ones == other.total_covered_more_than_ones and
                self.hash_table == other.hash_table)
