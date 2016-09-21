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
# Copyright: Red Hat Inc. 2016
# Author: Cleber Rosa <crosa@redhat.com>

import os
from setuptools import setup, find_packages


root_path = os.path.abspath(os.path.join("..", ".."))
version_file = os.path.join(root_path, 'VERSION')
VERSION = open(version_file, 'r').read().strip()

setup(name='avocado_result_html',
      description='Avocado HTML Report for Jobs',
      version=VERSION,
      author='Avocado Developers',
      author_email='avocado-devel@redhat.com',
      url='http://avocado-framework.github.io/',
      packages=find_packages(),
      include_package_data=True,
      install_requires=['avocado-framework', 'pystache'],
      entry_points={
          'avocado.plugins.cli': [
              'html = avocado_result_html:HTML',
          ],
          'avocado.plugins.result': [
              'html = avocado_result_html:HTMLResult',
          ]}
      )
