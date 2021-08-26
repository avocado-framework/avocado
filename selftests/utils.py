import logging
import os
import sys
import tempfile
import unittest

import pkg_resources

#: The base directory for the avocado source tree
BASEDIR = os.path.dirname(os.path.abspath(__file__))
BASEDIR = os.path.abspath(os.path.join(BASEDIR, os.path.pardir))

#: The name of the avocado test runner entry point
AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD",
                         "%s -m avocado" % sys.executable)


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


def temp_dir_prefix(klass):
    """
    Returns a standard name for the temp dir prefix used by the tests
    """
    return 'avocado_%s_' % klass.__class__.__name__


def get_temporary_config(klass):
    """
    Creates a temporary bogus config file
    returns base directory, dictionary containing the temporary data dir
    paths and the configuration file contain those same settings
    """
    prefix = temp_dir_prefix(klass)
    base_dir = tempfile.TemporaryDirectory(prefix=prefix)
    test_dir = os.path.join(base_dir.name, 'tests')
    os.mkdir(test_dir)
    data_directory = os.path.join(base_dir.name, 'data')
    os.mkdir(data_directory)
    cache_dir = os.path.join(data_directory, 'cache')
    os.mkdir(cache_dir)
    mapping = {'base_dir': base_dir.name,
               'test_dir': test_dir,
               'data_dir': data_directory,
               'logs_dir': os.path.join(base_dir.name, 'logs'),
               'cache_dir': cache_dir}
    temp_settings = ('[datadir.paths]\n'
                     'base_dir = %(base_dir)s\n'
                     'test_dir = %(test_dir)s\n'
                     'data_dir = %(data_dir)s\n'
                     'cache_dirs = ["%(cache_dir)s"]\n'
                     'logs_dir = %(logs_dir)s\n') % mapping
    config_file = tempfile.NamedTemporaryFile('w', dir=base_dir.name, delete=False)
    config_file.write(temp_settings)
    config_file.close()
    return base_dir, mapping, config_file


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
        for section in ('unit', 'functional'):
            start_dir = os.path.join(selftests_dir, section)
            suite.addTests(loader.discover(start_dir=start_dir,
                                           top_level_dir=basedir))
    if plugin_selftests is None:
        plugin_selftests = list(PLUGINS.keys())
    for plugin_dir in plugin_selftests:
        plugin_name = PLUGINS.get(plugin_dir, None)
        if python_module_available(plugin_name):
            path = os.path.join(basedir, 'optional_plugins',
                                plugin_dir, 'tests')
            suite.addTests(loader.discover(start_dir=path, top_level_dir=path))
    return suite


def skipOnLevelsInferiorThan(level):
    return unittest.skipIf(int(os.environ.get("AVOCADO_CHECK_LEVEL", 0)) < level,
                           "Skipping test that take a long time to run, are "
                           "resource intensive or time sensitive")


def skipUnlessPathExists(path):
    return unittest.skipUnless(os.path.exists(path),
                               ('File or directory at path "%s" used in test is'
                                ' not available in the system' % path))


class TestCaseTmpDir(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(self)
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)
        os.chdir(BASEDIR)

    def tearDown(self):
        self.tmpdir.cleanup()
