import logging
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


def setup_avocado_loggers():
    """
    Setup avocado loggers to contain at least one logger

    This is required for tests that directly utilize avocado.Test classes
    because they require those loggers to be configured. Without this
    it might (py2) result in infinite recursion while attempting to log
    "No handlers could be found for logger ..." message.
    """
    for name in ('', 'avocado.test', 'avocado.app'):
        logger = logging.getLogger(name)
        if not logger.handlers:
            logger.handlers.append(logging.NullHandler())


#: The plugin module names and directories under optional_plugins
PLUGINS = {'varianter_yaml_to_mux': 'avocado-framework-plugin-varianter-yaml-to-mux',
           'runner_remote': 'avocado-framework-plugin-runner-remote',
           'runner_vm': 'avocado-framework-plugin-runner-vm',
           'varianter_cit': 'avocado-framework-plugin-varianter-cit',
           'html': 'avocado-framework-plugin-result-html'}


def test_suite(base_selftests=True, plugin_selftests=None):
    '''
    Returns a test suite with all selftests found

    This includes tests on available optional plugins directories

    :param base_selftests: if the base selftests directory should be included
    :type base_selftests: bool
    :param plugin_selftests: the list optional plugin directories to include
                             or None to include all
    :type plugin_selftests: list or None
    :rtype: unittest.TestSuite
    '''
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    selftests_dir = os.path.dirname(os.path.abspath(__file__))
    basedir = os.path.dirname(selftests_dir)
    if base_selftests:
        for section in ('unit', 'functional', 'doc'):
            start_dir = os.path.join(selftests_dir, section)
            suite.addTests(loader.discover(start_dir=start_dir,
                                           top_level_dir=basedir))
    if plugin_selftests is None:
        plugin_selftests = PLUGINS.keys()
    for plugin_dir in plugin_selftests:
        plugin_name = PLUGINS.get(plugin_dir, None)
        if python_module_available(plugin_name):
            path = os.path.join(basedir, 'optional_plugins',
                                plugin_dir, 'tests')
            suite.addTests(loader.discover(start_dir=path, top_level_dir=path))
    return suite
