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
try:
    from setuptools import find_namespace_packages
except ImportError:
    packages = ["avocado_ansible"]
else:
    packages = find_namespace_packages(include=["avocado_ansible"])

VERSION = open("VERSION", "r", encoding="utf-8").read().strip()

setup(
    name="avocado-framework-plugin-ansible",
    description="Adds to Avocado the ability to use ansible modules as dependencies for tests",
    long_description="Adds to Avocado the ability to use ansible modules as dependencies for tests",
    long_description_content_type="text/x-rst",
    version=VERSION,
    author="Avocado Developers",
    author_email="avocado-devel@redhat.com",
    url="http://avocado-framework.github.io/",
    packages=packages,
    include_package_data=True,
    install_requires=[
        f"avocado-framework=={VERSION}",
        "cffi",
        "pycparser",
        "ansible-core",
    ],
    test_suite="tests",
    entry_points={
        "console_scripts": [
            "avocado-runner-ansible-module = avocado_ansible.module:main",
        ],
        "avocado.plugins.runnable.runner": [
            "ansible-module = avocado_ansible.module:AnsibleModuleRunner"
        ],
    },
)
