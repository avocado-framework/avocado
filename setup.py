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
# pylint: disable=E0611

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import avocado.version


def get_settings_dir():
    settings_system_wide = os.path.join('/etc', 'avocado')
    settings_local_install = os.path.join('etc', 'avocado')
    if 'VIRTUAL_ENV' in os.environ:
        return settings_local_install
    else:
        return settings_system_wide


def get_tests_dir():
    settings_system_wide = os.path.join('/usr', 'share', 'avocado', 'tests')
    settings_local_install = os.path.join('tests')
    if 'VIRTUAL_ENV' in os.environ:
        return settings_local_install
    else:
        return settings_system_wide


def get_docs_dir():
    settings_system_wide = os.path.join('/usr', 'share', 'doc', 'avocado')
    settings_local_install = ''
    if 'VIRTUAL_ENV' in os.environ:
        return settings_local_install
    else:
        return settings_system_wide


def get_data_files():
    data_files = [(get_settings_dir(), ['etc/settings.ini'])]
    data_files += [(get_tests_dir(), glob.glob('examples/tests/*.py'))]
    for data_dir in glob.glob('examples/tests/*.data'):
        fmt_str = '%s/*' % data_dir
        for f in glob.glob(fmt_str):
            data_files += [(os.path.join(get_tests_dir(), os.path.basename(data_dir)), [f])]
    data_files.append((get_docs_dir(), ['man/avocado.rst']))
    return data_files


def _get_plugin_resource_files(path):
    """
    Given a path, return all the files in there to package
    """
    flist = []
    for root, _, files in sorted(os.walk(path)):
        for name in files:
            fullname = os.path.join(root, name)
            flist.append(fullname[len('avocado/plugins/'):])
    return flist


def get_requirements():
    requirements = []
    with open('requirements.txt', 'r') as req:
        req_contents = req.read()
        for line in req_contents.splitlines():
            if not line.startswith("#"):
                line = line.split("#")[0].strip()
                requirements.append("%s" % line)
    return requirements

setup(name='avocado',
      version=avocado.version.VERSION,
      description='Avocado Test Framework',
      author='Lucas Meneghel Rodrigues',
      author_email='lmr@redhat.com',
      url='http://github.com/avocado-framework/avocado',
      packages=['avocado',
                'avocado.cli',
                'avocado.core',
                'avocado.external',
                'avocado.linux',
                'avocado.utils',
                'avocado.plugins'],
      package_data={'avocado.plugins': _get_plugin_resource_files('avocado/plugins/resources')},
      data_files=get_data_files(),
      scripts=['scripts/avocado'],
      install_requires=get_requirements())
