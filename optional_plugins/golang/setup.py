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

from setuptools import setup

# Handle systems with setuptools < 40
try:
    from setuptools import find_namespace_packages
except ImportError:
    packages = ['avocado_golang']
else:
    packages = find_namespace_packages(include=['avocado_golang'])

VERSION = open("VERSION", "r", encoding='utf-8').read().strip()

setup(name='avocado-framework-plugin-golang',
      description='Avocado Plugin for Execution of Golang tests',
      version=VERSION,
      author='Avocado Developers',
      author_email='avocado-devel@redhat.com',
      url='http://avocado-framework.github.io/',
      packages=packages,
      include_package_data=True,
      install_requires=[f'avocado-framework=={VERSION}'],
      test_suite='tests',
      entry_points={
          'console_scripts': [
              'avocado-runner-golang = avocado_golang.runner:main',
          ],
          'avocado.plugins.resolver': [
              'golang = avocado_golang.golang:GolangResolver',
          ],
          'avocado.plugins.runnable.runner': [
              'golang = avocado_golang.runner:GolangRunner'
          ]}
      )
