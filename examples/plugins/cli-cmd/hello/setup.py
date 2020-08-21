from setuptools import setup

if __name__ == '__main__':
    setup(name='avocado-hello-world-option',
          version='1.0',
          description='Avocado Hello World CLI command with config option',
          py_modules=['hello_option'],
          entry_points={
              'avocado.plugins.cli.cmd': ['hello_option = hello_option:HelloWorld'],
              }
          )
