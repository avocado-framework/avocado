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

import os

from setuptools import setup

# Handle systems with setuptools < 40
try:
    from setuptools import find_namespace_packages
except ImportError:
    packages = ["avocado_robot"]
else:
    packages = find_namespace_packages(include=["avocado_robot"])

BASE_PATH = os.path.dirname(__file__)
with open(os.path.join(BASE_PATH, "VERSION"), "r", encoding="utf-8") as version_file:
    VERSION = version_file.read().strip()


def get_long_description():
    with open(os.path.join(BASE_PATH, "README.rst"), "rt", encoding="utf-8") as readme:
        readme_contents = readme.read()
    return readme_contents


setup(
    name="avocado-framework-plugin-robot",
    version=VERSION,
    description="Avocado Plugin for Execution of Robot Framework tests",
    long_description=get_long_description(),
    long_description_content_type="text/x-rst",
    author="Avocado Developers",
    author_email="avocado-devel@redhat.com",
    url="http://avocado-framework.github.io/",
    packages=packages,
    include_package_data=True,
    install_requires=[
        f"avocado-framework=={VERSION}",
        "robotframework>=4.1, <=6.1.1; python_version < '3.8'",
        "robotframework>=4.1, <7.0; python_version >= '3.8'",
    ],
    test_suite="tests",
    entry_points={
        "console_scripts": [
            "avocado-runner-robot = avocado_robot.runner:main",
        ],
        "avocado.plugins.runnable.runner": ["robot = avocado_robot.runner:RobotRunner"],
        "avocado.plugins.resolver": ["robot = avocado_robot.robot:RobotResolver"],
    },
)
