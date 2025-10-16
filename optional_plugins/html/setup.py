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
# Copyright: Red Hat Inc. 2016
# Author: Cleber Rosa <crosa@redhat.com>

# Minimal setup.py for backward compatibility and egg builds.
# Metadata moved to pyproject.toml.

import os

from setuptools import find_packages, setup

BASE_PATH = os.path.dirname(__file__)
with open(os.path.join(BASE_PATH, "VERSION"), "r", encoding="utf-8") as version_file:
    VERSION = version_file.read().strip()

setup(
    name="avocado-framework-plugin-result-html",
    version=VERSION,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        f"avocado-framework=={VERSION}",
        "jinja2",
        "markupsafe<3.0.0",
    ],
    entry_points={
        "avocado.plugins.cli": [
            "html = avocado_result_html:HTML",
        ],
        "avocado.plugins.init": [
            "html = avocado_result_html:HTMLInit",
        ],
        "avocado.plugins.result": [
            "html = avocado_result_html:HTMLResult",
        ],
    },
)
