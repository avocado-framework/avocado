import os
import pkg_resources
import sys
import unittest

try:
    from unittest import mock
except ImportError:
    import mock


#: The base directory for the avocado source tree
BASEDIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

#: The name of the avocado test runner entry point
AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD",
                         "%s ./scripts/avocado" % sys.executable)


def recent_mock():
    '''
    Checks if a recent and capable enough mock library is available

    On Python 2.7, it requires at least mock version 2.0.  On Python 3,
    mock from the standard library is used, but Python 3.6 or later is
    required.

    Also, it assumes that on a future Python major version, functionality
    won't regress.
    '''
    if sys.version_info[0] < 3:
        major = int(mock.__version__.split('.')[0])
        return major >= 2
    elif sys.version_info[0] == 3:
        return sys.version_info[1] >= 6
    return True


def python_module_available(module_name):
    '''
    Checks if a given Python module is available

    :param module_name: the name of the module
    :type module_name: str
    :returns: if the Python module is available in the system
    :rtype: bool
    '''
    try:
        pkg_resources.require(module_name)
        return True
    except pkg_resources.DistributionNotFound:
        return False


def test_suite():
    '''
    Returns a test suite with all selftests found

    This includes tests on available optional plugins directories

    :rtype: unittest.TestSuite
    '''
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    selftests_dir = os.path.dirname(os.path.abspath(__file__))
    basedir = os.path.dirname(selftests_dir)
    for section in ('unit', 'functional', 'doc'):
        suite.addTests(loader.discover(start_dir=os.path.join(selftests_dir, section),
                                       top_level_dir=basedir))
    plugins = (('avocado-framework-plugin-varianter-yaml-to-mux',
                'varianter_yaml_to_mux'),
               ('avocado-framework-plugin-runner-remote',
                'runner_remote'),
               ('avocado-framework-plugin-runner-vm',
                'runner_vm'),
               ('avocado-framework-plugin-varianter-cit',
                'varianter_cit'),
               ('avocado-framework-plugin-result-html',
                'html'))
    for plugin_name, plugin_dir in plugins:
        if python_module_available(plugin_name):
            path = os.path.join(basedir, 'optional_plugins',
                                plugin_dir, 'tests')
            suite.addTests(loader.discover(start_dir=path, top_level_dir=path))
    return suite
