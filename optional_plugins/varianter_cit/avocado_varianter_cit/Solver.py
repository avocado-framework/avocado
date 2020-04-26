import itertools

from .Parameter import Parameter


class Solver:
    OR = "||"
    EQUALS = "="
    PARAMETER = 0
    VALUE = 2

    def __init__(self, data, constraints):
        self.data = data
        self.constraints = constraints
        self.parameters = []

        self.simplify_constraints()
        constraint_size = len(self.constraints)
        self.read_constraints()
        self.compute_constraints()
        self.simplify_constraints()
        while constraint_size != len(self.constraints):
            constraint_size = len(self.constraints)
            self.parameters = []
            self.read_constraints()
            self.compute_constraints()
            self.simplify_constraints()

    def read_constraints(self):
        # creates new parameters with their names
        for i, values_size in enumerate(self.data):
            self.parameters.append(Parameter(i, i, range(values_size)))
        for constraint in self.constraints:
            for index, pair in enumerate(constraint):
                self.parameters[pair.name].add_constraint(constraint,
                                                          pair.value,
                                                          index)

    def compute_constraints(self):
        for p in self.parameters:
            if p.is_full:
                array = [c for c in p.constraints if len(c) != 0]
                con = list(itertools.product(*array))
                if len(con[0]) == 0:
                    raise ValueError("Constraints are not satisfiable")
                for constraint in con:
                    constraint_array = set()
                    for c in range(len(constraint)):
                        for pair in range(len(constraint[c])):
                            constraint_array.add(constraint[c][pair])
                    constraint_array = sorted(constraint_array,
                                              key=lambda x: int(x.name))

                    has_subset = False
                    remove = set()
                    for c in self.constraints:
                        if len(c) < len(constraint_array):
                            if set(c) < set(constraint_array):
                                has_subset = True
                                break
                        if len(c) > len(constraint_array):
                            if set(c) > set(constraint_array):
                                remove.add(c)
                    if not has_subset:
                        self.constraints.add(tuple(constraint_array))
                    for r in remove:
                        self.constraints.remove(r)

    def simplify_constraints(self):
        items_to_remove = set()
        copy = list(self.constraints.copy())
        for i in range(len(copy)):
            is_brake = False
            for j in range(len(copy[i])):
                for k in range(j + 1, len(copy[i])):
                    if copy[i][j].name == copy[i][k].name:
                        items_to_remove.add(copy[i])
                        is_brake = True
                        break
                if is_brake:
                    break
            if is_brake:
                continue
            for j in range(len(copy)):
                if j != i:
                    if len(copy[i]) < len(copy[j]):
                        if set(copy[i]).issubset(set(copy[j])):
                            items_to_remove.add(copy[j])
        for item in items_to_remove:
            self.constraints.remove(item)

    def clean_hash_table(self, combination_matrix, t_value):
        for constraint in self.constraints:
            if len(constraint) > t_value:
                continue
            parameters_in_constraint = []
            for pair in constraint:
                parameters_in_constraint.append(pair.name)
            for c in itertools.combinations(range(len(self.data)), t_value):
                if set(parameters_in_constraint).issubset(c):
                    value_array = []
                    counter = 0
                    for value in c:
                        if value == constraint[counter].name:
                            value_array.append([constraint[counter].value])
                            if (counter + 1) != len(constraint):
                                counter += 1
                        else:
                            value_array.append(list(range(0, self.data[value])))
                    for key in itertools.product(*value_array):
                        combination_matrix.del_cell(c, key)

    def get_possible_values(self, row, parameter):
        """
        Compute all possible values for the given parameter.

        These values are based on constraints and already picked values
        of other parameters.

        :param row: row with picked values. -1 means an unpicked value.
        :type row: list
        :param parameter: index of the parameter
         whose we want to know the values
        :type parameter: int
        :return: all possible values for the given parameter
        :rtype: list
        """
        def is_permitted_value(one_value_constraints):
            if one_value_constraints is None:
                return True
            if len(one_value_constraints) == 0:
                return False

            for constraints in one_value_constraints:
                is_ok = False
                for constraint in constraints:
                    if row[constraint.name] != constraint.value:
                        is_ok = True
                        break
                if not is_ok:
                    return False
            return True

        return [i for i, c in enumerate(self.parameters[parameter].constraints)
                if is_permitted_value(c)]
