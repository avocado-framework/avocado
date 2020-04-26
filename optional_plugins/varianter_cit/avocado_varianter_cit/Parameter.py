class Pair:

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __str__(self):
        return str(self.name) + " != " + str(self.value)

    def __eq__(self, other):
        return self.name == other.name and self.value == other.value

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__str__())


class Parameter:

    def __init__(self, name, parameter_id, values):
        self.name = name
        self.id = parameter_id
        self.values = values
        self._constrained_values_number = 0
        self.constraints = [None]*len(values)

    def add_constraint(self, constraint, value, index):
        """
        Append new constraint to the parameter.

        The constraint is placed under the parameter value which is affected by
        this constraint. And this value is also deleted from the constraint,
        because is defined by the index in the 'self.constraints' list.

        :param constraint: will be appended to the parameter constraints
        :type constraint: list
        :param value: parameter value which is is affected by new constraint
        :type value: int
        :param index: index of that value inside the constraint
        :type index: int
        """
        if self.constraints[value] is None:
            self._constrained_values_number += 1
            self.constraints[value] = []
        array = list(constraint)
        array.pop(index)
        if len(array) != 0:
            self.constraints[value].append(array)

    @property
    def is_full(self):
        return self._constrained_values_number == len(self.values)

    def get_value_index(self, value):
        return self.values.index(value)

    def get_size(self):
        return len(self.values)
