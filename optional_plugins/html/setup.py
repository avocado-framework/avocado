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
# Copyright: Red Hat Inc. 2016
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
        suites.append(TestSuite.from_config(config_check, "PLUGIN_html"))

        # Test if the result file was created
        check_file_exists = ('%s:test_check_file_exists'
                             % (__file__))
        config_check_file_exists = {
            'run.references': [check_file_exists],
            'run.test_runner': 'runner',
            'run.dict_variants': [
                {'namespace': 'job.run.result.html.enabled',
                 'value': True,
                 'file': 'results.html',
                 'assert': True},

                {'namespace': 'job.run.result.html.enabled',
                 'value': False,
                 'file': 'results.html',
                 'assert': False},
            ]
        }
        suites.append(TestSuite.from_config(config_check_file_exists,
                                            "PLUGIN_html-job-api-enabled"))

        # Test if a file was created
        check_output_file = ('%s:test_check_output_file'
                             % (__file__))
        config_check_output_file = {
            'run.references': [check_output_file],
            'run.test_runner': 'runner',
            'run.dict_variants': [
                {'namespace': 'job.run.result.html.output',
                 'file': 'custom.html',
                 'assert': True},
            ]
        }
        suites.append(TestSuite.from_config(config_check_output_file,
                                            "PLUGIN_html-job-api-output"))

        config = {'core.show': ['app'],
                  'run.test_runner': 'nrunner'}

        with Job(config, suites) as j:
            exit_code = j.run()
        return exit_code

    def initialize_options(self):
        """Set default values for options."""

    def finalize_options(self):
        """Post-process options."""


setup(name='avocado-framework-plugin-result-html',
      description='Avocado HTML Report for Jobs',
      version=VERSION,
      author='Avocado Developers',
      author_email='avocado-devel@redhat.com',
      url='http://avocado-framework.github.io/',
      packages=find_packages(),
      include_package_data=True,
      install_requires=['avocado-framework==%s' % VERSION, 'jinja2'],
      cmdclass={'test': Test},
      entry_points={
          'avocado.plugins.cli': [
              'html = avocado_result_html:HTML',
          ],
          'avocado.plugins.init': [
              'html = avocado_result_html:HTMLInit',
          ],
          'avocado.plugins.result': [
              'html = avocado_result_html:HTMLResult',
          ]}
      )
