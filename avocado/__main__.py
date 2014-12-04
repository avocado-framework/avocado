"""
Main entry point when called by 'python -m'.
"""

import sys

from avocado.cli.app import AvocadoApp

if sys.argv[0].endswith('__main__.py'):
    sys.argv[0] = 'python -m avocado'

main = AvocadoApp()
main.run()
