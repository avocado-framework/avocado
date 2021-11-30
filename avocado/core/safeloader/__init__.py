# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2014-2016,2018
# Authors: Cleber Rosa <crosa@redhat.com>
#          Lukas Doktor <ldoktor@redhat.com>

"""
Safe (AST based) test loader module utilities
"""

from avocado.core.safeloader.core import (find_avocado_tests,
                                          find_python_unittests)

__all__ = ['find_avocado_tests', 'find_python_unittests']
