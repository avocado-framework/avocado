from setuptools import setup

name = 'magic'
module = 'avocado_magic'
resolver_ep = '%s = %s.resolver:%s' % (name, module, 'MagicResolver')
runner_ep = '%s = %s.runner:%s' % (name, module, 'MagicRunner')
runner_script = 'avocado-runner-%s = %s.runner:main' % (name, module)


if __name__ == '__main__':
    setup(name=name,
          version='1.0',
          description='Avocado "magic" test type',
          py_modules=[module],
          entry_points={
              'avocado.plugins.resolver': [resolver_ep],
              'avocado.plugins.runnable.runner': [runner_ep],
              'console_scripts': [runner_script],
              }
          )
