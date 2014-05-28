import yaml
import os
import re


def cartesian_product(iterable):
    """
    Produces the cartesian product of an iterable.
    """
    if not iterable:
        yield ()
    else:
        for a in iterable[0]:
            for prod in cartesian_product(iterable[1:]):
                yield (a,) + prod


class Parser(object):

    def __init__(self, filename):
        config_path = os.path.abspath(filename)
        with open(config_path, 'r') as config_file_obj:
            contents = config_file_obj.read()
        self.data_structure = yaml.load(contents)

    def get_dicts(self, only_filter=None):
        args_dict = self.data_structure['input']['args']
        variables = sorted(args_dict.keys())
        iterable = []
        test_name = self.data_structure['name']

        for variable in variables:
            iterable.append(args_dict[variable])

        for combination in cartesian_product(iterable):
            p_dict = {}
            shortname = test_name
            for p_name, p_value in zip(variables, combination):
                shortname += ".%s_%s" % (p_name, p_value)
                p_dict[p_name] = p_value
            if only_filter is not None:
                if re.search(only_filter, shortname):
                    p_dict['shortname'] = shortname
                    yield p_dict
            else:
                p_dict['shortname'] = shortname
                yield p_dict
