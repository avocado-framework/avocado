import imp
import inspect
import os
import sys

from avocado.core import test
from avocado.utils import stacktrace


class TestError(test.Test):
    """
    Generic test error.
    """

    def __init__(self, *args, **kwargs):
        exception = kwargs.pop('exception')
        test.Test.__init__(self, *args, **kwargs)
        self.exception = exception

    def test(self):
        self.error(self.exception)


def load_test(test_factory):
    """
    Load test from the test factory.

    :param test_factory: a pair of test class and parameters.
    :type test_factory: tuple
    :return: an instance of :class:`avocado.core.test.Test`.
    """
    test_class, test_parameters = test_factory
    if 'modulePath' in test_parameters:
        test_path = test_parameters.pop('modulePath')
    else:
        test_path = None
    if isinstance(test_class, str):
        module_name = os.path.basename(test_path).split('.')[0]
        test_module_dir = os.path.abspath(os.path.dirname(test_path))
        # Tests with local dir imports need this
        try:
            sys.path.insert(0, test_module_dir)
            f, p, d = imp.find_module(module_name, [test_module_dir])
            test_module = imp.load_module(module_name, f, p, d)
        except:  # pylint: disable=W0702
            # On load_module exception we fake the test class and pass
            # the exc_info as parameter to be logged.
            test_parameters['methodName'] = 'test'
            exception = stacktrace.prepare_exc_info(sys.exc_info())
            test_parameters['exception'] = exception
            return TestError(**test_parameters)
        finally:
            if test_module_dir in sys.path:
                sys.path.remove(test_module_dir)
        for _, obj in inspect.getmembers(test_module):
            if (inspect.isclass(obj) and obj.__name__ == test_class and
                    inspect.getmodule(obj) == test_module):
                if issubclass(obj, test.Test):
                    test_class = obj
                    break
    if test_class is test.DryRunTest:
        test_parameters['modulePath'] = test_path
    if 'run.results_dir' in test_parameters:
        test_parameters['base_logdir'] = test_parameters.pop('run.results_dir')
    test_instance = test_class(**test_parameters)

    return test_instance
