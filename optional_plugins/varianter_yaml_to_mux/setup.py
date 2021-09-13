#!/bin/env python3
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
# Copyright: Red Hat Inc. 2017
# Author: Cleber Rosa <crosa@redhat.com>

import glob

from setuptools import Command, find_packages, setup

VERSION = open("VERSION", "r").read().strip()


class Test(Command):
    """Run tests"""

    description = "Run tests"
    user_options = []

    def run(self):
        # This must go there otherwise avocado must be installed for all targets
        from avocado.core.job import Job
        from avocado.core.suite import TestSuite
        suites = []
        pattern = 'tests/*'
        config_check = {
            'run.references': glob.glob(pattern),
            'run.test_runner': 'nrunner',
            'run.ignore_missing_references': True,
            'job.output.testlogs.statuses': ['FAIL']
            }
        suites.append(TestSuite.from_config(config_check, "PLUGIN_varianter-yaml-to-mux"))

        config = {'core.show': ['app'],
                  'run.test_runner': 'nrunner'}

        with Job(config, suites) as j:
            exit_code = j.run()
        return exit_code

    def initialize_options(self):
        """Set default values for options."""

    def finalize_options(self):
        """Post-process options."""


setup(name='avocado-framework-plugin-varianter-yaml-to-mux',
      description='Avocado Varianter plugin to parse YAML file into variants',
      version=VERSION,
      author='Avocado Developers',
      author_email='avocado-devel@redhat.com',
      url='http://avocado-framework.github.io/',
      packages=find_packages(exclude=('tests*',)),
      include_package_data=True,
      install_requires=['avocado-framework==%s' % VERSION, 'PyYAML>=4.2b2'],
      test_suite='tests',
      cmdclass={'test': Test},
      entry_points={
          "avocado.plugins.init": [
              "yaml_to_mux = avocado_varianter_yaml_to_mux:YamlToMuxInit",
          ],
          "avocado.plugins.cli": [
              "yaml_to_mux = avocado_varianter_yaml_to_mux:YamlToMuxCLI",
          ],
          "avocado.plugins.varianter": [
              "yaml_to_mux = avocado_varianter_yaml_to_mux:YamlToMux"]})
