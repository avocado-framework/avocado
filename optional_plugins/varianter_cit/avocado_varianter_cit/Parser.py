import re


class Parser:

    @staticmethod
    def parse(file_object):
        """
        Parsing of input file with parameters and constraints

        :param file_object: input file for parsing
        :return: array of parameters and set of constraints
        """

        rx_parameter_name = re.compile(r"(.+?)\[")
        rx_parameter_value = re.compile(r"\[(.+?)\]")
        rx_constraint = re.compile(r".+?!=.+?")
        parameters = []
        constraints = set()
        is_parameters = None

        for line in file_object:
            line = line.strip()
            if not line:
                continue
            if line == "PARAMETERS":
                is_parameters = True
                continue
            if line == "CONSTRAINTS":
                is_parameters = False
                continue
            if is_parameters is None:
                raise ValueError("Invalid file")
            if is_parameters:
                # Searching for parameter name
                match = rx_parameter_name.search(line)
                if match is None:
                    raise ValueError('Parameter name is missing')
                parameter_name = match.group(1).strip()

                # Searching for parameter_values
                match = rx_parameter_value.search(line)
                if match is None:
                    raise ValueError('Parameter values are missing')
                parameter_values = [x.strip() for x in match.group(1).split(',')]
                if len(parameter_values) != len(set(parameter_values)):
                    raise ValueError('Parameter values has duplicities')

                parameters.append((parameter_name, parameter_values))
            else:
                constraints_data = line.split("||")
                array = []
                for constraint in constraints_data:
                    value_index = 1
                    if not rx_constraint.match(constraint):
                        raise ValueError("Invalid format of constraint")
                    constraint_data = [x.strip() for x in constraint.split("!=")]
                    # Searching for parameter name in constraint
                    constraint_name = next((i for i, p in enumerate(parameters)
                                            if p[0] == constraint_data[0]), None)
                    if constraint_name is None:
                        # If first value inside constraint wasn't parameter name try second value
                        try:
                            constraint_name = next((i for i, p in
                                                    enumerate(parameters)
                                                    if p[0] == constraint_data[1]))
                            value_index = 0
                        except StopIteration:
                            raise ValueError('Name in constraint not match with names in parameters')
                    try:
                        # Checking if value in constraint is matching with parameter values
                        constraint_value = parameters[constraint_name][1]\
                            .index(constraint_data[value_index])
                    except ValueError:
                        raise ValueError('Value in constraint not match with values in parameters')
                    array.append((constraint_name, constraint_value))
                array.sort(key=lambda x: int(x[0]))
                constraints.add(tuple(array))
        return parameters, constraints
