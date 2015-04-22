"""
Main entry point when called by 'python -m'.
"""

import sys

from avocado.core.app import AvocadoApp

if __name__ == '__main__':
    main = AvocadoApp()
    sys.exit(main.run())
