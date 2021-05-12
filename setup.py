#!/bin/env python
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
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

import glob
import os
import sys
from abc import abstractmethod
from distutils.command.clean import clean
from subprocess import CalledProcessError, call, check_call

from setuptools import Command, find_packages, setup

# pylint: disable=E0611


BASE_PATH = os.path.dirname(__file__)
with open(os.path.join(BASE_PATH, 'VERSION'), 'r') as version_file:
    VERSION = version_file.read().strip()


def get_long_description():
    with open(os.path.join(BASE_PATH, 'README.rst'), 'r') as readme:
        readme_contents = readme.read()
    return readme_contents


class Clean(clean):
    """Our custom command to get rid of junk files after build."""

    description = "Get rid of scratch, byte files and build stuff."

    def run(self):
        super().run()
        call(('rm -rf MANIFEST BUILD BUILDROOT SPECS RPMS SRPMS SOURCES',
              'PYPI_UPLOAD ./build ./dist'), shell=True)
        call('rm -rf ./man/avocado.1 ./docs/build', shell=True)
        call('rm -rf /var/tmp/avocado* /tmp/avaocado*', shell=True)
        call('find . -name "*.egg-info" -exec rm -rv {} +', shell=True)
        call('find . -name "*.pyc" -exec rm -rv {} +', shell=True)
        call('find . -name __pycache__ -type d -exec rm -rv {} +', shell=True)
        call('find ./docs/source/api/ -name "*.rst" -exec rm -rv {} +',
             shell=True)
        self.clean_optional_plugins()

    @staticmethod
    def clean_optional_plugins():
        root_dir = os.getcwd()
        for plugin in map(os.path.dirname,
                          glob.glob('./optional_plugins/*/setup.py')):
            print(">> CLEANING {}".format(plugin))
            os.chdir(plugin)
            call('{} setup.py clean --all'.format(sys.executable), shell=True)
            os.chdir(root_dir)


class SimpleCommand(Command):
    """Make Command implementation simpler."""

    user_options = []

    @abstractmethod
    def run(self):
        """Run when command is invoked."""

    def initialize_options(self):
        """Set default values for options."""

    def finalize_options(self):
        """Post-process options."""


class Linter(SimpleCommand):
    """Lint Python source code."""

    description = 'Run logical, stylistic, analytical and formatter checks.'

    def run(self):
        try:
            check_call('selftests/inspekt-indent.sh')
            check_call('selftests/inspekt-style.sh')
            check_call('selftests/isort.sh')
            check_call('selftests/lint.sh')
            check_call('selftests/signedoff-check.sh')
            check_call('selftests/spell.sh')
        except CalledProcessError as e:
            print("Failed during lint checks: ", e)
            sys.exit(128)


if __name__ == '__main__':
    # Force "make develop" inside the "readthedocs.org" environment
    if os.environ.get("READTHEDOCS") and "install" in sys.argv:
        os.system("make develop")
    setup(name='avocado-framework',
          version=VERSION,
          description='Avocado Test Framework',
          long_description=get_long_description(),
          author='Avocado Developers',
          author_email='avocado-devel@redhat.com',
          url='http://avocado-framework.github.io/',
          license="GPLv2+",
          classifiers=[
              "Development Status :: 5 - Production/Stable",
              "Intended Audience :: Developers",
              "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
              "Natural Language :: English",
              "Operating System :: POSIX",
              "Topic :: Software Development :: Quality Assurance",
              "Topic :: Software Development :: Testing",
              "Programming Language :: Python :: 3",
              "Programming Language :: Python :: 3.6",
              "Programming Language :: Python :: 3.7",
              "Programming Language :: Python :: 3.8",
              ],
          packages=find_packages(exclude=('selftests*',)),
          include_package_data=True,
          entry_points={
              'console_scripts': [
                  'avocado = avocado.core.main:main',
                  'avocado-runner = avocado.core.nrunner:main',
                  'avocado-runner-noop = avocado.core.nrunner:main',
                  'avocado-runner-exec = avocado.core.nrunner:main',
                  'avocado-runner-exec-test = avocado.core.nrunner:main',
                  'avocado-runner-python-unittest = avocado.core.nrunner:main',
                  'avocado-runner-avocado-instrumented = avocado.core.runners.avocado_instrumented:main',
                  'avocado-runner-tap = avocado.core.runners.tap:main',
                  'avocado-runner-requirement-package = avocado.core.runners.requirement_package:main',
                  'avocado-software-manager = avocado.utils.software_manager.main:main',
                  ],
              "avocado.plugins.init": [
                  "xunit = avocado.plugins.xunit:XUnitInit",
                  "jsonresult = avocado.plugins.jsonresult:JSONInit",
                  "sysinfo = avocado.plugins.sysinfo:SysinfoInit",
                  "tap = avocado.plugins.tap:TAPInit",
                  "jobscripts = avocado.plugins.jobscripts:JobScriptsInit",
                  "dict_variants = avocado.plugins.dict_variants:DictVariantsInit",
                  "json_variants = avocado.plugins.json_variants:JsonVariantsInit",
                  "run = avocado.plugins.run:RunInit",
                  "podman = avocado.plugins.spawners.podman:PodmanSpawnerInit",
                  "nrunner = avocado.plugins.runner_nrunner:RunnerInit",
                  "testlogsui = avocado.plugins.testlogs:TestLogsUIInit",
              ],
              'avocado.plugins.cli': [
                  'wrapper = avocado.plugins.wrapper:Wrapper',
                  'xunit = avocado.plugins.xunit:XUnitCLI',
                  'json = avocado.plugins.jsonresult:JSONCLI',
                  'journal = avocado.plugins.journal:Journal',
                  'replay_legacy = avocado.plugins.legacy.replay:Replay',
                  'tap = avocado.plugins.tap:TAP',
                  'zip_archive = avocado.plugins.archive:ArchiveCLI',
                  'json_variants = avocado.plugins.json_variants:JsonVariantsCLI',
                  'nrunner = avocado.plugins.runner_nrunner:RunnerCLI',
                  'podman = avocado.plugins.spawners.podman:PodmanCLI',
                  ],
              'avocado.plugins.cli.cmd': [
                  'config = avocado.plugins.config:Config',
                  'distro = avocado.plugins.distro:Distro',
                  'exec-path = avocado.plugins.exec_path:ExecPath',
                  'variants = avocado.plugins.variants:Variants',
                  'list = avocado.plugins.list:List',
                  'run = avocado.plugins.run:Run',
                  'sysinfo = avocado.plugins.sysinfo:SysInfo',
                  'plugins = avocado.plugins.plugins:Plugins',
                  'diff = avocado.plugins.diff:Diff',
                  'vmimage = avocado.plugins.vmimage:VMimage',
                  'assets = avocado.plugins.assets:Assets',
                  'jobs = avocado.plugins.jobs:Jobs',
                  'replay = avocado.plugins.replay:Replay',
                  ],
              'avocado.plugins.job.prepost': [
                  'jobscripts = avocado.plugins.jobscripts:JobScripts',
                  'teststmpdir = avocado.plugins.teststmpdir:TestsTmpDir',
                  'human = avocado.plugins.human:HumanJob',
                  'merge_files = avocado.plugins.expected_files_merge:FilesMerge',
                  'testlogsui = avocado.plugins.testlogs:TestLogsUI',
                  ],
              'avocado.plugins.result': [
                  'xunit = avocado.plugins.xunit:XUnitResult',
                  'json = avocado.plugins.jsonresult:JSONResult',
                  'zip_archive = avocado.plugins.archive:Archive',
                  ],
              'avocado.plugins.result_events': [
                  'human = avocado.plugins.human:Human',
                  'tap = avocado.plugins.tap:TAPResult',
                  'journal = avocado.plugins.journal:JournalResult',
                  'fetchasset = avocado.plugins.assets:FetchAssetJob',
                  'sysinfo = avocado.plugins.sysinfo:SysInfoJob',
                  'testlogging = avocado.plugins.testlogs:TestLogging',
                  ],
              'avocado.plugins.varianter': [
                  'json_variants = avocado.plugins.json_variants:JsonVariants',
                  'dict_variants = avocado.plugins.dict_variants:DictVariants',
                  ],
              'avocado.plugins.resolver': [
                  'exec-test = avocado.plugins.resolvers:ExecTestResolver',
                  'python-unittest = avocado.plugins.resolvers:PythonUnittestResolver',
                  'avocado-instrumented = avocado.plugins.resolvers:AvocadoInstrumentedResolver',
                  'tap = avocado.plugins.resolvers:TapResolver',
                  ],
              'avocado.plugins.runner': [
                  'runner = avocado.plugins.runner:TestRunner',
                  'nrunner = avocado.plugins.runner_nrunner:Runner',
                  ],
              'avocado.plugins.runnable.runner': [
                  ('avocado-instrumented = avocado.core.'
                   'runners.avocado_instrumented:AvocadoInstrumentedTestRunner'),
                  'tap = avocado.core.runners.tap:TAPRunner',
                  ],
              'avocado.plugins.spawner': [
                  'process = avocado.plugins.spawners.process:ProcessSpawner',
                  'podman = avocado.plugins.spawners.podman:PodmanSpawner',
                  ],
              },
          zip_safe=False,
          test_suite='selftests',
          python_requires='>=3.6',
          cmdclass={'clean': Clean,
                    'lint': Linter},
          install_requires=['setuptools'])
