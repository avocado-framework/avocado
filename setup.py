#!/usr/bin/env python3
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
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Minimal setup.py for backward compatibility.

All configuration has been moved to pyproject.toml.
This file is kept for backward compatibility with tools that still expect setup.py,
and for building egg distributions (bdist_egg) which is not yet supported by
PEP 517 build tools.
"""

import os

from setuptools import find_packages, setup

# Read version for egg builds (bdist_egg doesn't fully support pyproject.toml)
BASE_PATH = os.path.dirname(__file__)
with open(os.path.join(BASE_PATH, "VERSION"), "r", encoding="utf-8") as f:
    VERSION = f.read().strip()

# For egg builds, we need to specify packages explicitly
# All other configuration is in pyproject.toml
setup(
    name="avocado-framework",
    version=VERSION,
    packages=find_packages(exclude=("selftests*",)),
    include_package_data=True,
    zip_safe=False,
)
