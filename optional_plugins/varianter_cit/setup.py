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
# Authors: Amador Pahim <amador@pahim.org>
#          Bestoun S. Ahmed <bestoon82@gmail.com>
#          Cleber Rosa <crosa@redhat.com>


from setuptools import setup

# Handle systems with setuptools < 40
try:
    from setuptools import find_namespace_packages
except ImportError:
    packages = ['avocado_varianter_cit']
else:
    packages = find_namespace_packages(include=['avocado_varianter_cit'])

VERSION = open("VERSION", "r", encoding='utf-8').read().strip()

setup(name='avocado-framework-plugin-varianter-cit',
      description='Varianter with combinatorial capabilities',
      version=open("VERSION", "r", encoding='utf-8').read().strip(),
      author='Avocado Developers',
      author_email='avocado-devel@redhat.com',
      url='http://avocado-framework.github.io/',
      packages=packages,
      include_package_data=True,
      install_requires=[f'avocado-framework=={VERSION}'],
      test_suite='tests',
      entry_points={
          'avocado.plugins.cli': [
              'varianter_cit = avocado_varianter_cit.varianter_cit:VarianterCitCLI',
          ],
          "avocado.plugins.varianter": [
              "varianter_cit = avocado_varianter_cit.varianter_cit:VarianterCit",
          ]}
      )
