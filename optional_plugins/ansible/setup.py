#!/bin/env python3
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
# Copyright: Red Hat Inc. 2022
# Author: Cleber Rosa <crosa@redhat.com>

from setuptools import setup

# Handle systems with setuptools < 40
VERSION = open("VERSION", "r", encoding="utf-8").read().strip()

setup(
    install_requires=[
        f"avocado-framework=={VERSION}",
        "cffi",
        "pycparser",
        "ansible-core",
    ],
    test_suite="tests",
)
