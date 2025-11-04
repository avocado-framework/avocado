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

# Minimal setup.py for backward compatibility and egg builds.
# Metadata moved to pyproject.toml.

from setuptools import find_namespace_packages, setup

VERSION = open("VERSION", "r", encoding="utf-8").read().strip()

setup(
    name="avocado-framework-plugin-ansible",
    version=VERSION,
    packages=find_namespace_packages(include=["avocado_ansible"]),
    include_package_data=True,
    install_requires=[
        f"avocado-framework=={VERSION}",
        "cffi==1.17.1; python_version<'3.10'",
        "cffi; python_version>='3.10'",
        "cryptography<46.0.0; python_version<'3.10'",
        "pycparser",
        "ansible-core",
        "markupsafe<3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "avocado-runner-ansible-module = avocado_ansible.module:main",
        ],
        "avocado.plugins.runnable.runner": [
            "ansible-module = avocado_ansible.module:AnsibleModuleRunner"
        ],
    },
)
