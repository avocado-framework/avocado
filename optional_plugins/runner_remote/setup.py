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

import os
import sys
sys.path.append(os.path.join('..', '..'))
from avocado.utils import distro

from setuptools import setup, find_packages

if sys.version_info[0] == 3:
    fabric = 'Fabric3'
else:
    fabric = 'fabric>=1.5.4,<2.0.0'
detected_distro = distro.detect()
if detected_distro.name == 'fedora' and int(detected_distro.version) >= 29:
    fabric = 'Fabric3>=1.1.4,<2.0.0'


setup(name='avocado-framework-plugin-runner-remote',
      description='Avocado Runner for Remote Execution',
      version=open("VERSION", "r").read().strip(),
      author='Avocado Developers',
      author_email='avocado-devel@redhat.com',
      url='http://avocado-framework.github.io/',
      packages=find_packages(exclude=('tests*',)),
      include_package_data=True,
      install_requires=['avocado-framework', fabric],
      test_suite='tests',
      entry_points={
          'avocado.plugins.cli': [
              'remote = avocado_runner_remote:RemoteCLI',
          ]}
      )
