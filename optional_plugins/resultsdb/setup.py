#!/bin/env python
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

from setuptools import setup, find_packages


setup(name='avocado-framework-plugin-resultsdb',
      description='Avocado Plugin to propagate Job results to Resultsdb',
      version=open("VERSION", "r").read().strip(),
      author='Avocado Developers',
      author_email='avocado-devel@redhat.com',
      url='http://avocado-framework.github.io/',
      packages=find_packages(),
      include_package_data=True,
      install_requires=['avocado-framework', 'resultsdb-api'],
      entry_points={
          'avocado.plugins.cli': [
              'resultsdb = avocado_resultsdb:ResultsdbCLI',
              ],
          'avocado.plugins.result_events': [
              'resultsdb = avocado_resultsdb:ResultsdbResult',
              ]})
