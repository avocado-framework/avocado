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

from distutils.core import setup

import avocado.version


VIRTUAL_ENV = 'VIRTUAL_ENV' in os.environ


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
    data_files = [(get_dir(['etc', 'avocado']), ['etc/avocado/avocado.conf'])]
    data_files += [(get_dir(['etc', 'avocado', 'conf.d']),
                    ['etc/avocado/conf.d/README'])]
    data_files += [(get_dir(['etc', 'avocado', 'sysinfo']),
                    ['etc/avocado/sysinfo/commands', 'etc/avocado/sysinfo/files',
                     'etc/avocado/sysinfo/profilers'])]
    data_files += [(get_tests_dir(), glob.glob('examples/tests/*.py'))]
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
    data_files += [(get_dir(['usr', 'share', 'avocado', 'api'], ['api']),
                    glob.glob('examples/api/*/*.py'))]
    data_files.append((get_avocado_libexec_dir(), glob.glob('libexec/*')))
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


def get_long_description():
    with open('README.rst', 'r') as req:
        req_contents = req.read()
    return req_contents

if __name__ == '__main__':
    setup(name='avocado',
          version=avocado.version.VERSION,
          description='Avocado Test Framework',
          long_description=get_long_description(),
          author='Avocado Developers',
          author_email='avocado-devel@redhat.com',
          url='http://avocado-framework.github.io/',
          packages=['avocado',
                    'avocado.core',
                    'avocado.core.plugins',
                    'avocado.linux',
                    'avocado.utils',
                    'avocado.core.remote',
                    'avocado.restclient',
                    'avocado.core.restclient',
                    'avocado.core.restclient.cli',
                    'avocado.core.restclient.cli.args',
                    'avocado.core.restclient.cli.actions'],
          package_data={'avocado.core.plugins': _get_plugin_resource_files(
              'avocado/plugins/resources')},
          data_files=get_data_files(),
          scripts=['scripts/avocado',
                   'scripts/avocado-rest-client'])
