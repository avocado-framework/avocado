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
# Copyright: Red Hat Inc. 2015
# Author: Cleber Rosa <cleber@redhat.com>

from setuptools import setup

if __name__ == '__main__':
    setup(name='avocadotap',
          version='0.0.1',
          description='Avocado TAP plugin',
          author='Avocado Developers',
          author_email='avocado-devel@redhat.com',
          url='http://avocado-framework.github.io/',
          packages=['avocadotap'],
          entry_points={
              'avocado.plugins.results': [
                  'tap = avocadotap.tap:TAPResult',
                  ],
              'avocado.plugins.cli.run': [
                  'tap = avocadotap.tap:TAPRun',
                  ]
              },
          )
