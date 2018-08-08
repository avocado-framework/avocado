import os
import sys
import unittest

#: The base directory for the avocado source tree
BASEDIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

#: The name of the avocado test runner entry point
AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD",
                         "%s ./scripts/avocado" % sys.executable)
