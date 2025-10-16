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
# Copyright: Red Hat Inc. 2024
# Author: Harvey Lynden <hlynden@redhat.com>

# Minimal setup.py for backward compatibility and egg builds.
# Metadata moved to pyproject.toml.

import os

from setuptools import find_packages, setup

BASE_PATH = os.path.dirname(__file__)
with open(os.path.join(BASE_PATH, "VERSION"), "r", encoding="utf-8") as version_file:
    VERSION = version_file.read().strip()

setup(
    name="avocado-framework-plugin-result-mail",
    version=VERSION,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[f"avocado-framework=={VERSION}"],
    entry_points={
        "avocado.plugins.init": [
            "notification = avocado_result_mail.result_mail:MailInit",
        ],
        "avocado.plugins.job.prepost": [
            "notification = avocado_result_mail.result_mail:Mail",
        ],
    },
)
