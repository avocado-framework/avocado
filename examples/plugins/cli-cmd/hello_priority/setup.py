from setuptools import setup

if __name__ == '__main__':
    setup(name='avocado-hello-world-priority',
          version='1.0',
          description='Avocado Hello World CLI command, with priority',
          py_modules=['hello_priority'],
          entry_points={
              'avocado.plugins.cli.cmd': ['hello = hello_priority:HelloWorld'],
              }
          )
