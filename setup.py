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
                  ('/usr/share/avocado/tests/doublefail', ['tests/doublefail/doublefail.py']),

                  ('/usr/share/avocado/tests/doublefree', ['tests/doublefree/doublefree.py']),
                  ('/usr/share/avocado/tests/doublefree/data', ['tests/doublefree/data/doublefree.c']),

                  ('/usr/share/avocado/tests/errortest', ['tests/errortest/errortest.py']),
                  ('/usr/share/avocado/tests/failtest', ['tests/failtest/failtest.py']),

                  ('/usr/share/avocado/tests/fiotest', ['tests/fiotest/fiotest.py']),
                  ('/usr/share/avocado/tests/fiotest/data', glob.glob('tests/fiotest/data/*')),

                  ('/usr/share/avocado/tests/gendata', ['tests/gendata/gendata.py']),

                  ('/usr/share/avocado/tests/linuxbuild', ['tests/linuxbuild/linuxbuild.py']),
                  ('/usr/share/avocado/tests/linuxbuild/data', glob.glob('tests/linuxbuild/data/*')),

                  ('/usr/share/avocado/tests/multiplextest', glob.glob('tests/multiplextest/*')),
                  ('/usr/share/avocado/tests/skiptest', ['tests/skiptest/skiptest.py']),
                  ('/usr/share/avocado/tests/sleeptenmin', ['tests/sleeptenmin/sleeptenmin.py']),
                  ('/usr/share/avocado/tests/sleeptest', glob.glob('tests/sleeptest/*')),

                  ('/usr/share/avocado/tests/synctest', glob.glob('tests/synctest/synctest.py')),
                  ('/usr/share/avocado/tests/synctest/data', ['tests/synctest/data/synctest.tar.bz2']),

                  ('/usr/share/avocado/tests/timeouttest', ['tests/timeouttest/timeouttest.py']),

                  ('/usr/share/avocado/tests/trinity', ['tests/trinity/trinity.py']),
                  ('/usr/share/avocado/tests/trinity/data', ['tests/trinity/data/trinity-1.4.tar.bz2']),

                  ('/usr/share/avocado/tests/warntest', ['tests/warntest/warntest.py']),
                  ('/usr/share/avocado/tests/whiteboard', glob.glob('tests/whiteboard/*'))],
      scripts=['scripts/avocado'])
