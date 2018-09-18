import os
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
