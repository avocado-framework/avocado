from setuptools import setup

if __name__ == '__main__':
    setup(name='avocado-hello-world-parser',
          version='1.0',
          description='Avocado Hello World CLI command with config parser',
          py_modules=['hello_parser'],
          entry_points={
              'avocado.plugins.cli.cmd': ['hello_parser = hello_parser:HelloWorld'],
              }
          )
