from setuptools import setup

name = 'magic'
module = 'avocado_magic'
resolver_ep = f"{name} = {module}.resolver:MagicResolver"
discoverer_ep = f"{name} = {module}.resolver:MagicDiscoverer"
runner_ep = f"{name} = {module}.runner:MagicRunner"
runner_script = f'avocado-runner-{name} = {module}.runner:main'


if __name__ == '__main__':
    setup(name=name,
          version='1.0',
          description='Avocado "magic" test type',
          py_modules=[module],
          entry_points={
              'avocado.plugins.resolver': [resolver_ep],
              'avocado.plugins.discoverer': [discoverer_ep],
              'avocado.plugins.runnable.runner': [runner_ep],
              'console_scripts': [runner_script],
              }
          )
