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
# pylint: disable=E0611

from setuptools import setup, find_packages

BASE_PATH = os.path.dirname(__file__)
with open(os.path.join(BASE_PATH, 'VERSION'), 'r') as version_file:
    VERSION = version_file.read().strip()
VIRTUAL_ENV = (hasattr(sys, 'real_prefix') or 'VIRTUAL_ENV' in os.environ)


def get_dir(system_path=None, virtual_path=None):
    """
    Retrieve VIRTUAL_ENV friendly path
    :param system_path: Relative system path
    :param virtual_path: Overrides system_path for virtual_env only
    :return: VIRTUAL_ENV friendly path
    """
    if virtual_path is None:
        virtual_path = system_path
    if VIRTUAL_ENV:
        if virtual_path is None:
            virtual_path = []
        return os.path.join(*virtual_path)
    else:
        if system_path is None:
            system_path = []
        return os.path.join(*(['/'] + system_path))


def get_tests_dir():
    return get_dir(['usr', 'share', 'avocado', 'tests'], ['tests'])


def get_avocado_libexec_dir():
    if VIRTUAL_ENV:
        return get_dir(['libexec'])
    elif os.path.exists('/usr/libexec'):    # RHEL-like distro
        return get_dir(['usr', 'libexec', 'avocado'])
    else:                                   # Debian-like distro
        return get_dir(['usr', 'lib', 'avocado'])


def get_data_files():
    data_files = []
    data_files += [(get_tests_dir(), glob.glob('examples/tests/*.py'))]
    data_files += [(get_tests_dir(), glob.glob('examples/tests/*.sh'))]
    for data_dir in glob.glob('examples/tests/*.data'):
        fmt_str = '%s/*' % data_dir
        for f in glob.glob(fmt_str):
            data_files += [(os.path.join(get_tests_dir(),
                                         os.path.basename(data_dir)), [f])]
    data_files.append((get_dir(['usr', 'share', 'doc', 'avocado'], ['.']),
                       ['man/avocado.rst', 'man/avocado-rest-client.rst']))
    data_files += [(get_dir(['usr', 'share', 'avocado', 'wrappers'],
                            ['wrappers']),
                    glob.glob('examples/wrappers/*.sh'))]

    data_files.append((get_avocado_libexec_dir(), glob.glob('libexec/*')))
    data_files += [(get_dir(['usr', 'share', 'avocado', 'gdb-prerun-scripts'],
                            ['gdb-prerun-scripts']),
                    glob.glob('examples/gdb-prerun-scripts/*'))]
    data_files += [(get_dir(['usr', 'share', 'avocado', 'plugins',
                             'job-pre-post'],
                            ['plugins/job-pre-post']),
                    glob.glob('examples/plugins/job-pre-post/README.rst'))]
    data_files += [(get_dir(['usr', 'share', 'avocado', 'plugins',
                             'job-pre-post', 'mail'],
                            ['plugins/job-pre-post/mail']),
                    glob.glob('examples/plugins/job-pre-post/mail/*'))]
    data_files += [(get_dir(['usr', 'share', 'avocado', 'plugins',
                             'job-pre-post', 'sleep'],
                            ['plugins/job-pre-post/sleep']),
                    glob.glob('examples/plugins/job-pre-post/sleep/*'))]
    data_files += [(get_dir(['usr', 'share', 'avocado', 'yaml_to_mux'],
                            ['yaml_to_mux']),
                    glob.glob('examples/yaml_to_mux/*.yaml'))]
    data_files += [(get_dir(['usr', 'share', 'avocado', 'yaml_to_mux', 'hw'],
                            ['yaml_to_mux/hw']),
                    glob.glob('examples/yaml_to_mux/hw/*.yaml'))]
    data_files += [(get_dir(['usr', 'share', 'avocado', 'yaml_to_mux', 'os'],
                            ['yaml_to_mux/os']),
                    glob.glob('examples/yaml_to_mux/os/*.yaml'))]
    data_files += [(get_dir(['usr', 'share', 'avocado', 'yaml_to_mux_loader'],
                            ['yaml_to_mux_loader']),
                    glob.glob('examples/yaml_to_mux_loader/*.yaml'))]
    data_files += [(get_dir(['usr', 'share', 'avocado', 'varianter_pict'],
                            ['varianter_pict']),
                    glob.glob('examples/varianter_pict/*.pict'))]
    return data_files


def _get_resource_files(path, base):
    """
    Given a path, return all the files in there to package
    """
    flist = []
    for root, _, files in sorted(os.walk(path)):
        for name in files:
            fullname = os.path.join(root, name)
            flist.append(fullname[len(base):])
    return flist


def get_long_description():
    with open(os.path.join(BASE_PATH, 'README.rst'), 'r') as req:
        req_contents = req.read()
    return req_contents


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
              "Programming Language :: Python :: 2.7",
              ],
          packages=find_packages(exclude=('selftests*',)),
          include_package_data=True,
          data_files=get_data_files(),
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
              },
          zip_safe=False,
          test_suite='selftests',
          python_requires='>=2.7',
          install_requires=['stevedore>=0.14'])
