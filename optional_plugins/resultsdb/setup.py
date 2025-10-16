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
# Copyright: Red Hat Inc. 2017
# Author: Amador Pahim <apahim@redhat.com>

# Minimal setup.py for backward compatibility and egg builds.
# Metadata moved to pyproject.toml.

import os

from setuptools import find_namespace_packages, setup

BASE_PATH = os.path.dirname(__file__)
with open(os.path.join(BASE_PATH, "VERSION"), "r", encoding="utf-8") as version_file:
    VERSION = version_file.read().strip()

setup(
    name="avocado-framework-plugin-resultsdb",
    version=VERSION,
    packages=find_namespace_packages(include=["avocado_resultsdb"]),
    include_package_data=True,
    install_requires=[
        f"avocado-framework=={VERSION}",
        "resultsdb-api==2.1.5",
        "urllib3<2.3.0; python_version < '3.9'",
    ],
    entry_points={
        "avocado.plugins.cli": [
            "resultsdb = avocado_resultsdb.resultsdb:ResultsdbCLI",
        ],
        "avocado.plugins.result_events": [
            "resultsdb = avocado_resultsdb.resultsdb:ResultsdbResultEvent",
        ],
        "avocado.plugins.result": [
            "resultsdb = avocado_resultsdb.resultsdb:ResultsdbResult",
        ],
    },
)
