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
        self.is_full = False
        self.name = name
        self.id = parameter_id
        self.values = values
        self.constrained_values = set()
        self.constraints = {}
        for i in range(len(values)):
            self.constraints[i] = []

    def add_constraint(self, constraint):
        array = []
        value = None
        for pair in constraint:
            if pair.name == self.name:
                self.constrained_values.add(pair.value)
                value = pair.value
            else:
                array.append(pair)
        if len(self.constrained_values) == len(self.values):
            self.is_full = True
        if len(array) != 0:
            self.constraints[value].append(array)

    def get_constraints(self):
        array = []
        for key in self.constraints:
            array.append(self.constraints[key])
        return array

    def get_value_index(self, value):
        return self.values.index(value)

    def get_size(self):
        return len(self.values)
