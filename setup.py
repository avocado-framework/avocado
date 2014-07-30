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
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

import glob
# pylint: disable=E0611
from distutils.core import setup

import avocado.version

setup(name='avocado',
      version=avocado.version.VERSION,
      description='Avocado Test Framework',
      author='Lucas Meneghel Rodrigues',
      author_email='lmr@redhat.com',
      url='http://github.com/avocado-framework/avocado',
      packages=['avocado',
                'avocado.cli',
                'avocado.core',
                'avocado.linux',
                'avocado.utils',
                'avocado.plugins'],
      data_files=[('/etc/avocado', ['etc/settings.ini']),
                  ('/usr/share/avocado/tests/sleeptest', glob.glob('tests/sleeptest/*')),
                  ('/usr/share/avocado/tests/failtest', glob.glob('tests/failtest/*')),
                  ('/usr/share/avocado/tests/synctest', glob.glob('tests/synctest/synctest.py')),
                  ('/usr/share/avocado/tests/synctest/data', glob.glob('tests/synctest/data/synctest.tar.bz2'))],
      scripts=['scripts/avocado'])
