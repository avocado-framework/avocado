import glob
from distutils.core import setup

import avocado.version

setup(name='avocado',
      version=avocado.version.VERSION,
      description='Avocado Test Framework',
      author='Lucas Meneghel Rodrigues',
      author_email='lmr@redhat.com',
      url='http://autotest.github.com',
      packages=['avocado',
                'avocado.cli',
                'avocado.core',
                'avocado.linux',
                'avocado.utils',
                'avocado.plugins'],
      data_files=[('/etc/avocado', ['etc/settings.ini']),
                  ('/usr/share/avocado/tests/sleeptest', glob.glob('tests/sleeptest/*')),
                  ('/usr/share/avocado/tests/failtest', glob.glob('tests/failtest/*'))],
      scripts=['scripts/avocado'])
