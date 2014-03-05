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
                'avocado.utils'
                ],
      scripts=['scripts/avocado-run'])
