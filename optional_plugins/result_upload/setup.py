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
# Copyright: Virtuozzo Inc. 2017
# Authors: Dmitry Monakhov <dmonakhov@openvz.org>

from setuptools import find_packages, setup

VERSION = open("VERSION", "r").read().strip()

setup(name='avocado-framework-plugin-result-upload',
      description='Avocado Plugin to propagate Job results to remote host',
      version=VERSION,
      author='Avocado Developers',
      author_email='avocado-devel@redhat.com',
      url='http://avocado-framework.github.io/',
      packages=find_packages(),
      include_package_data=True,
      install_requires=['avocado-framework==%s' % VERSION],
      entry_points={
          'avocado.plugins.cli': [
              'results_upload = avocado_result_upload:ResultUploadCLI',
              ],
          'avocado.plugins.result': [
              'results_upload = avocado_result_upload:ResultUpload',
              ]})
