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

from setuptools import find_packages, setup

VERSION = open("VERSION", "r").read().strip()

setup(name='avocado-framework-plugin-robot',
      description='Avocado Plugin for Execution of Robot Framework tests',
      version=VERSION,
      author='Avocado Developers',
      author_email='avocado-devel@redhat.com',
      url='http://avocado-framework.github.io/',
      packages=find_packages(),
      include_package_data=True,
      install_requires=['avocado-framework==%s' % VERSION,
                        'robotframework>=4.1'],
      test_suite='tests',
      entry_points={
          'console_scripts': [
              'avocado-runner-robot = avocado_robot.runner:main',
          ],
          'avocado.plugins.resolver': [
              'robot = avocado_robot:RobotResolver'
          ]}
      )
