import itertools


class CombinationRow:

    """
    Row object store all combinations between two parameters into dictionary.
    Keys in dictionary are values of combinations and values in dictionary are
    information about coverage. Row object has information how many combinations
    are uncovered and how many of them are covered more than ones.
    """

    def __init__(self, input_data, t_value, parameters):
        """
        :param input_data: list of data from user
        :param t_value: t number from user
        :param parameters: the tuple of parameters whose combinations Row object represents
        """

        self.hash_table = {}
        self.covered_more_than_ones = 0
        self.uncovered = 0
        array = []
        "Creation of combinations"
        for i in range(t_value):
            array.append(list(range(input_data[parameters[i]])))
        for i in itertools.product(*array):
            self.uncovered += 1
            self.hash_table[i] = 0

    def cover_cell(self, key):
        """
        Cover one combination inside Row

        :param key: combination to be covered
        :return: number of new covered combinations and number of new covered combinations more than ones
        """

        old_uncovered = self.uncovered
        old_covered_more_than_ones = self.covered_more_than_ones
        value = self.hash_table[tuple(key)]
        if value is not None:
            if value == 0:
                self.uncovered -= 1
            elif value == 1:
                self.covered_more_than_ones += 1
            self.hash_table[tuple(key)] += 1

        return self.uncovered - old_uncovered, self.covered_more_than_ones - old_covered_more_than_ones

    def uncover_cell(self, key):
        """
        Uncover one combination inside Row

        :param key: combination to be uncovered
        :return: number of new covered combinations and number of new covered combinations more than ones
        """

        old_uncovered = self.uncovered
        old_covered_more_than_ones = self.covered_more_than_ones
        value = self.hash_table[tuple(key)]
        if value is not None and value > 0:
            if value == 1:
                self.uncovered += 1
            elif value == 2:
                self.covered_more_than_ones -= 1
            self.hash_table[tuple(key)] -= 1

        return self.uncovered - old_uncovered, self.covered_more_than_ones - old_covered_more_than_ones

    def completely_uncover(self):
        """
        Uncover all combinations inside Row
        """

        self.uncovered = 0
        self.covered_more_than_ones = 0
        for key, value in self.hash_table.items():
            if value is not None:
                self.hash_table[key] = 0
                self.uncovered += 1

    def del_cell(self, key):
        """
        Disable one combination. If combination is disabled it means that
        the combination does not match the constraints

        :param key: combination to be disabled
        :return: number of new covered combinations
        """

        key = tuple(key)
        if self.hash_table[key] is not None:
            self.hash_table[key] = None
            self.uncovered -= 1
            return -1
        else:
            return 0

    def is_valid(self, key):
        """
        Is the combination match the constraints.

        :param key: combination to valid
        """

        key = tuple(key)
        if self.hash_table.get(key, 0) is None:
            return False
        else:
            return True

    def get_all_uncovered_combinations(self):
        """
        :return: list of all uncovered combination
        """

        combinations = []
        for key, value in self.hash_table.items():
            if value == 0:
                combinations.append(key)
        return combinations

    def __eq__(self, other):
        return (self.covered_more_than_ones == other.covered_more_than_ones and self.uncovered == other.uncovered and
                self.hash_table == other.hash_table)
