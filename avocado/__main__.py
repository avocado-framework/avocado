"""
Main entry point when called by 'python -m'.
"""

from __future__ import absolute_import

import sys

from avocado.core.app import AvocadoApp

if __name__ == '__main__':
    main = AvocadoApp()
    sys.exit(main.run())
