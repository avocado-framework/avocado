import importlib
import inspect
import os
import sys

from avocado.core import test


def load_test(test_factory):
    """
    Load test from the test factory.

    :param test_factory: a pair of test class and parameters.
    :type test_factory: tuple
    :return: an instance of :class:`avocado.core.test.Test`.
    """
    test_class, test_parameters = test_factory
    if "run.results_dir" in test_parameters:
        test_parameters["base_logdir"] = test_parameters.pop("run.results_dir")
    if "modulePath" not in test_parameters:
        raise RuntimeError(
            'Test factory parameters is missing the module\'s path ("modulePath")'
        )

    test_path = test_parameters.pop("modulePath")
    module_name = os.path.basename(test_path).split(".")[0]
    test_module_dir = os.path.abspath(os.path.dirname(test_path))
    spec = importlib.util.spec_from_file_location(module_name, test_path)
    test_module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = test_module
    try:
        # Tests with local dir imports need this
        sys.path.insert(0, test_module_dir)
        spec.loader.exec_module(test_module)
    finally:
        if test_module_dir in sys.path:
            sys.path.remove(test_module_dir)
    for _, obj in inspect.getmembers(test_module):
        if (
            inspect.isclass(obj)
            and obj.__name__ == test_class
            and inspect.getmodule(obj) == test_module
            and issubclass(obj, test.Test)
        ):
            return obj(**test_parameters)
    raise ImportError(f'Failed to find/load class "{test_class}" in "{test_path}"')
