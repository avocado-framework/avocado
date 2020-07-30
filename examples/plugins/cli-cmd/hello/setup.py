from setuptools import setup

if __name__ == '__main__':
    setup(name='avocado-hello-world',
          version='1.0',
          description='Avocado Hello World CLI command',
          py_modules=['hello'],
          entry_points={
              'avocado.plugins.cli.cmd': ['hello = hello:HelloWorld'],
              }
          )
