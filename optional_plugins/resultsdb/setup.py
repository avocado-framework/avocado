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
    packages = ['avocado_resultsdb']
else:
    packages = find_namespace_packages(include=['avocado_resultsdb'])

VERSION = open("VERSION", "r", encoding='utf-8').read().strip()

setup(name='avocado-framework-plugin-resultsdb',
      description='Avocado Plugin to propagate Job results to Resultsdb',
      version=VERSION,
      author='Avocado Developers',
      author_email='avocado-devel@redhat.com',
      url='http://avocado-framework.github.io/',
      packages=packages,
      include_package_data=True,
      install_requires=[f'avocado-framework=={VERSION}',
                        'resultsdb-api==2.1.5'],
      entry_points={
          'avocado.plugins.cli': [
              'resultsdb = avocado_resultsdb.resultsdb:ResultsdbCLI',
              ],
          'avocado.plugins.result_events': [
              'resultsdb = avocado_resultsdb.resultsdb:ResultsdbResultEvent',
              ],
          'avocado.plugins.result': [
              'resultsdb = avocado_resultsdb.resultsdb:ResultsdbResult',
              ]})
