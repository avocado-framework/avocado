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
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

import argparse
import os
import shutil
import sys
from abc import abstractmethod
from distutils.command.clean import clean
from pathlib import Path
from subprocess import CalledProcessError, run

import setuptools.command.develop
from setuptools import Command, find_packages, setup

# pylint: disable=E0611


BASE_PATH = os.path.dirname(__file__)
with open(os.path.join(BASE_PATH, 'VERSION'), 'r', encoding='utf-8') as version_file:
    VERSION = version_file.read().strip()


def get_long_description():
    with open(os.path.join(BASE_PATH, 'README.rst'), 'rt',
              encoding='utf-8') as readme:
        readme_contents = readme.read()
    return readme_contents


def walk_plugins_setup_py(action, action_name=None,
                          directory=os.path.join(BASE_PATH, "optional_plugins")):

    if action_name is None:
        action_name = action[0].upper()

    for plugin in list(Path(directory).glob("*/setup.py")):
        parent_dir = plugin.parent
        print(f">> {action_name} {parent_dir}")
        run([sys.executable, "setup.py"] + action, cwd=parent_dir, check=True)


class Clean(clean):
    """Our custom command to get rid of junk files after build."""

    description = "Get rid of scratch, byte files and build stuff."

    def run(self):
        super().run()
        cleaning_list = ["PYPI_UPLOAD", "./build", "./dist",
                         "./man/avocado.1", "./docs/build"]

        cleaning_list += list(Path('/tmp/').glob(".avocado-*"))
        cleaning_list += list(Path('/var/tmp/').glob(".avocado-*"))
        cleaning_list += list(Path('.').rglob("*.egg-info"))
        cleaning_list += list(Path('.').rglob("*.pyc"))
        cleaning_list += list(Path('.').rglob("__pycache__"))
        cleaning_list += list(Path('./docs/source/api/').rglob("*.rst"))

        for e in cleaning_list:
            if not os.path.exists(e):
                continue
            if os.path.isfile(e):
                os.remove(e)
            if os.path.isdir(e):
                shutil.rmtree(e)

        self.clean_optional_plugins()

    @staticmethod
    def clean_optional_plugins():
        walk_plugins_setup_py(["clean", "--all"])


class Develop(setuptools.command.develop.develop):
    """Custom develop command."""

    user_options = setuptools.command.develop.develop.user_options + [
        ("external", None, "Install external plugins in development mode"),
        ("skip-optional-plugins", None,
         "Do not include in-tree optional plugins in development mode")
    ]

    boolean_options = setuptools.command.develop.develop.boolean_options + [
        'external',
        'skip-optional-plugins']

    def _walk_develop_plugins(self):
        if not self.skip_optional_plugins:
            walk_plugins_setup_py(action=["develop"] + self.action_options,
                                  action_name=self.action_name)

    @property
    def action_options(self):
        result = []
        if self.uninstall:
            result.append("--uninstall")
        if self.user:
            result.append("--user")
        return result

    @property
    def action_name(self):
        if self.uninstall:
            return "DEVELOP UNLINK"
        else:
            return "DEVELOP LINK"

    @property
    def external_plugins_path(self):
        try:
            d = os.getenv('AVOCADO_EXTERNAL_PLUGINS_PATH')
            if not os.path.exists(d):
                return None
            return os.path.abspath(d)
        except TypeError:
            return None

    def initialize_options(self):
        super().initialize_options()
        self.external = 0  # pylint: disable=W0201
        self.skip_optional_plugins = 0  # pylint: disable=W0201

    def handle_uninstall(self):
        """When uninstalling, we remove the plugins before Avocado."""
        self._walk_develop_plugins()
        super().run()

    def handle_install(self):
        """When installing, we install plugins after installing Avocado."""
        super().run()
        self._walk_develop_plugins()

    def handle_external(self):
        """Handles only external plugins.

        The current logic means that --external will not install Avocado.
        """
        d = self.external_plugins_path
        if d is None:
            msg = ("The variable AVOCADO_EXTERNAL_PLUGINS_PATH isn't "
                   "properly set")
            sys.exit(msg)

        walk_plugins_setup_py(action=["develop"] + self.action_options,
                              action_name=self.action_name, directory=d)

    def run(self):
        if self.external:
            self.handle_external()
        else:
            if not self.uninstall:
                self.handle_install()
            elif self.uninstall:
                self.handle_uninstall()


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
    """Lint Python source code. (Deprecated)"""

    description = 'Run logical, stylistic, analytical and formatter checks.'

    def run(self):
        print("This command is deprecated, please use instead: python3 setup.py test --static-checks")
        sys.exit()


class Test(SimpleCommand):
    """Run selftests"""

    description = 'Run selftests'
    user_options = [
        ("skip=", None, "Run all tests and skip listed tests, separated by comma"),
        ("select=", None, "Do not run any test, only these listed after, separated by comma"),
        ("disable-plugin-checks=", None, "Disable checks for one or more plugins (by directory name), separated by comma"),
        ("list-features", None, "Show the features tested by this test")
    ]

    def initialize_options(self):
        self.skip = []  # pylint: disable=W0201
        self.select = []  # pylint: disable=W0201
        self.disable_plugin_checks = []  # pylint: disable=W0201
        self.list_features = False  # pylint: disable=W0201

    def run(self):
        args = argparse.Namespace()
        args.skip = self.skip if len(self.skip) == 0 else [self.skip]
        args.select = self.select if len(self.select) == 0 else [self.select]
        args.disable_plugin_checks = self.disable_plugin_checks if len(self.disable_plugin_checks) == 0 else [self.disable_plugin_checks]
        args.list_features = self.list_features

        # Import here on purpose, otherwise it'll mess with install/develop commands
        import selftests.check
        sys.exit(selftests.check.main(args))


class Man(SimpleCommand):
    """Build man page"""

    description = 'Build man page.'

    def run(self):
        if shutil.which("rst2man"):
            cmd = "rst2man"
        elif shutil.which("rst2man.py"):
            cmd = "rst2man.py"
        else:
            sys.exit("rst2man not found, I can't build the manpage")

        try:
            run([cmd, "man/avocado.rst", "man/avocado.1"], check=True)
        except CalledProcessError as e:
            print("Failed manpage build: ", e)
            sys.exit(128)


class Plugin(SimpleCommand):
    """Handle plugins"""

    description = 'Handle plugins'
    user_options = [
        ("list", 'l', "List available plugins"),
        ("install=", 'i', "Plugin to install"),
        ("user", 'u', "User install")
    ]

    def initialize_options(self):
        self.list = False  # pylint: disable=W0201
        self.install = None  # pylint: disable=W0201
        self.user = False  # pylint: disable=W0201

    def run(self):

        plugins_list = []
        directory = os.path.join(BASE_PATH, "optional_plugins")
        for plugin in list(Path(directory).glob("*/setup.py")):
            plugins_list.append(plugin.parts[-2])

        if self.list or (not self.list and not self.install):
            print("List of available plugins:\n ", "\n  ".join(plugins_list))
            return

        if self.install in plugins_list:
            action = ["install"]
            if self.user:
                action += ["--user"]
            parent_dir = os.path.join(directory, self.install)
            run([sys.executable, "setup.py"] + action, cwd=parent_dir, check=True)
        else:
            print(self.install, "is not a known plugin. Please, check the list of available plugins.")
            return


if __name__ == '__main__':
    # Force "make develop" inside the "readthedocs.org" environment
    if os.environ.get("READTHEDOCS") and "install" in sys.argv:
        run(["/usr/bin/make", "develop"], check=True)
    setup(name='avocado-framework',
          version=VERSION,
          description='Avocado Test Framework',
          long_description=get_long_description(),
          author='Avocado Developers',
          author_email='avocado-devel@redhat.com',
          url='https://avocado-framework.github.io/',
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
              "Programming Language :: Python :: 3.9",
              "Programming Language :: Python :: 3.10",
              ],
          packages=find_packages(exclude=('selftests*',)),
          include_package_data=True,
          entry_points={
              'console_scripts': [
                  'avocado = avocado.core.main:main',
                  'avocado-runner = avocado.core.nrunner.__main__:main',
                  'avocado-runner-noop = avocado.plugins.runners.noop:main',
                  'avocado-runner-dry-run = avocado.plugins.runners.dry_run:main',
                  'avocado-runner-exec-test = avocado.plugins.runners.exec_test:main',
                  'avocado-runner-python-unittest = avocado.plugins.runners.python_unittest:main',
                  'avocado-runner-avocado-instrumented = avocado.plugins.runners.avocado_instrumented:main',
                  'avocado-runner-tap = avocado.plugins.runners.tap:main',
                  'avocado-runner-asset = avocado.plugins.runners.asset:main',
                  'avocado-runner-package = avocado.plugins.runners.package:main',
                  'avocado-runner-sysinfo = avocado.plugins.runners.sysinfo:main',
                  'avocado-software-manager = avocado.utils.software_manager.main:main',
                  'avocado-external-runner = scripts.external_runner:main',
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
                  "human = avocado.plugins.human:HumanInit",
              ],
              'avocado.plugins.cli': [
                  'xunit = avocado.plugins.xunit:XUnitCLI',
                  'json = avocado.plugins.jsonresult:JSONCLI',
                  'journal = avocado.plugins.journal:Journal',
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
                  'bystatus = avocado.plugins.bystatus:ByStatusLink',
                  'beaker = avocado.plugins.beaker_result:BeakerResult',
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
                  'nrunner = avocado.plugins.runner_nrunner:Runner',
                  ],
              'avocado.plugins.runnable.runner': [
                  ('avocado-instrumented = avocado.plugins.'
                   'runners.avocado_instrumented:AvocadoInstrumentedTestRunner'),
                  'tap = avocado.plugins.runners.tap:TAPRunner',
                  'noop = avocado.plugins.runners.noop:NoOpRunner',
                  'dry-run = avocado.plugins.runners.dry_run:DryRunRunner',
                  'exec-test = avocado.plugins.runners.exec_test:ExecTestRunner',
                  'python-unittest = avocado.plugins.runners.python_unittest:PythonUnittestRunner',
                  'asset = avocado.plugins.runners.asset:AssetRunner',
                  'package = avocado.plugins.runners.package:PackageRunner',
                  'sysinfo = avocado.plugins.runners.sysinfo:SysinfoRunner',
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
                    'develop': Develop,
                    'lint': Linter,
                    'man': Man,
                    'plugin': Plugin,
                    'test': Test},
          install_requires=['setuptools'])
