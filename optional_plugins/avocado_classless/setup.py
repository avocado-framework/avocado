#! /usr/bin/env python3

# SPDX-License-Identifier: GPL-2.0-or-later
#
# Copyright Red Hat
# Author: David Gibson <david@gibson.dropbear.id.au>
# Author: Cleber Rosa <crosa@redhat.com>

"""
Setup script for avocado-classless plugin
"""

import os

from setuptools import setup

# Handle systems with setuptools < 40
try:
    from setuptools import find_namespace_packages
except ImportError:
    packages = ["avocado_classless"]
else:
    packages = find_namespace_packages(include=["avocado_classless"])

BASE_PATH = os.path.dirname(__file__)
with open(os.path.join(BASE_PATH, "VERSION"), "r", encoding="utf-8") as version_file:
    VERSION = version_file.read().strip()


def get_long_description():
    with open(os.path.join(BASE_PATH, "README.rst"), "rt", encoding="utf-8") as readme:
        readme_contents = readme.read()
    return readme_contents


setup(
    name="avocado-framework-plugin-avocado-classless",
    version=VERSION,
    description="Avocado Plugin for classless tests",
    long_description=get_long_description(),
    long_description_content_type="text/x-rst",
    author="David Gibson",
    author_email="david@gibson.dropbear.id.au",
    url="http://avocado-framework.github.io/",
    packages=packages,
    include_package_data=True,
    install_requires=[
        f"avocado-framework=={VERSION}",
    ],
    entry_points={
        "console_scripts": [
            "avocado-runner-avocado-classless = avocado_classless.plugin:main",
        ],
        "avocado.plugins.runnable.runner": [
            "avocado-classless = avocado_classless.plugin:ClasslessRunner"
        ],
        "avocado.plugins.resolver": [
            "avocado-classless = avocado_classless.plugin:ClasslessResolver"
        ],
    },
)
