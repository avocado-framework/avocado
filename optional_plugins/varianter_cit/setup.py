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
# Authors: Amador Pahim <amador@pahim.org>
#          Bestoun S. Ahmed <bestoon82@gmail.com>
#          Cleber Rosa <crosa@redhat.com>

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
        suites.append(TestSuite.from_config(config_check, "PLUGIN_varianter-cit"))

        config = {'core.show': ['app'],
                  'run.test_runner': 'nrunner'}

        with Job(config, suites) as j:
            exit_code = j.run()
        return exit_code

    def initialize_options(self):
        """Set default values for options."""

    def finalize_options(self):
        """Post-process options."""


setup(name='avocado-framework-plugin-varianter-cit',
      description='Varianter with combinatorial capabilities',
      version=open("VERSION", "r").read().strip(),
      author='Avocado Developers',
      author_email='avocado-devel@redhat.com',
      url='http://avocado-framework.github.io/',
      packages=find_packages(),
      include_package_data=True,
      install_requires=['avocado-framework==%s' % VERSION],
      test_suite='tests',
      cmdclass={'test': Test},
      entry_points={
          'avocado.plugins.cli': [
              'varianter_cit = avocado_varianter_cit:VarianterCitCLI',
          ],
          "avocado.plugins.varianter": [
              "varianter_cit = avocado_varianter_cit:VarianterCit",
          ]}
      )
