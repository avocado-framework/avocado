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

import os
import sys
# pylint: disable=E0611

from setuptools import setup, find_packages

BASE_PATH = os.path.dirname(__file__)
with open(os.path.join(BASE_PATH, 'VERSION'), 'r') as version_file:
    VERSION = version_file.read().strip()


def get_long_description():
    with open(os.path.join(BASE_PATH, 'README.rst'), 'r') as req:
        req_contents = req.read()
    return req_contents


INSTALL_REQUIREMENTS = ['requests', 'stevedore>=0.14', 'six>=1.10.0', 'setuptools']

if sys.version_info[0] == 2:
    INSTALL_REQUIREMENTS.append('enum34')

if sys.version_info[0] == 3 and sys.version_info[1] <= 3:
    INSTALL_REQUIREMENTS.append('backports.lzma>=0.0.10')


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
              "Programming Language :: Python :: 2",
              "Programming Language :: Python :: 2.7",
              "Programming Language :: Python :: 3",
              "Programming Language :: Python :: 3.4",
              "Programming Language :: Python :: 3.5",
              "Programming Language :: Python :: 3.6",
              ],
          packages=find_packages(exclude=('selftests*',)),
          include_package_data=True,
          scripts=['scripts/avocado',
                   'scripts/avocado-rest-client'],
          entry_points={
              'avocado.plugins.cli': [
                  'envkeep = avocado.plugins.envkeep:EnvKeep',
                  'gdb = avocado.plugins.gdb:GDB',
                  'wrapper = avocado.plugins.wrapper:Wrapper',
                  'xunit = avocado.plugins.xunit:XUnitCLI',
                  'json = avocado.plugins.jsonresult:JSONCLI',
                  'journal = avocado.plugins.journal:Journal',
                  'replay = avocado.plugins.replay:Replay',
                  'tap = avocado.plugins.tap:TAP',
                  'zip_archive = avocado.plugins.archive:ArchiveCLI',
                  'json_variants = avocado.plugins.json_variants:JsonVariantsCLI',
                  ],
              'avocado.plugins.cli.cmd': [
                  'config = avocado.plugins.config:Config',
                  'distro = avocado.plugins.distro:Distro',
                  'exec-path = avocado.plugins.exec_path:ExecPath',
                  'multiplex = avocado.plugins.multiplex:Multiplex',
                  'variants = avocado.plugins.variants:Variants',
                  'list = avocado.plugins.list:List',
                  'run = avocado.plugins.run:Run',
                  'sysinfo = avocado.plugins.sysinfo:SysInfo',
                  'plugins = avocado.plugins.plugins:Plugins',
                  'diff = avocado.plugins.diff:Diff',
                  ],
              'avocado.plugins.job.prepost': [
                  'jobscripts = avocado.plugins.jobscripts:JobScripts',
                  'teststmpdir = avocado.plugins.teststmpdir:TestsTmpDir',
                  'human = avocado.plugins.human:HumanJob',
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
                  ],
              'avocado.plugins.varianter': [
                  'json_variants = avocado.plugins.json_variants:JsonVariants',
                 ],
              },
          zip_safe=False,
          test_suite='selftests',
          python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',
          install_requires=INSTALL_REQUIREMENTS)
