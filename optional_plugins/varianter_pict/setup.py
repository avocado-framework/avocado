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
# Author: Cleber Rosa <crosa@redhat.com>

from setuptools import find_packages, setup

VERSION = open("VERSION", "r").read().strip()

setup(name='avocado-framework-plugin-varianter-pict',
      description='Varianter with combinatorial capabilities by PICT',
      version=VERSION,
      author='Avocado Developers',
      author_email='avocado-devel@redhat.com',
      url='http://avocado-framework.github.io/',
      packages=find_packages(),
      include_package_data=True,
      install_requires=['avocado-framework==%s' % VERSION],
      entry_points={
          'avocado.plugins.cli': [
              'varianter_pict = avocado_varianter_pict:VarianterPictCLI',
          ],
          "avocado.plugins.varianter": [
              "varianter_pict = avocado_varianter_pict:VarianterPict",
          ]}
      )
