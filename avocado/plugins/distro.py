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
# Copyright: Red Hat Inc. 2015
# Author: Cleber Rosa <cleber@redhat.com>

import bz2
import json

from avocado.core import output
from avocado.plugins import plugin
from avocado.linux import distro as distro_utils


class SoftwarePackage(object):

    '''
    Definition of relevant information on a software package
    '''

    def __init__(self, name, version, release, checksum, arch):
        self.name = name
        self.version = version
        self.release = release
        self.checksum = checksum
        self.arch = arch

    def to_dict(self):
        '''
        Returns the representation as a dictionary
        '''
        return {'name': self.name,
                'version': self.version,
                'release': self.release,
                'checksum': self.checksum,
                'arch': self.arch}

    def to_json(self):
        '''
        Returns the representation of the distro as JSON
        '''
        return json.dumps(self.to_dict())


class DistroDef(distro_utils.LinuxDistro):

    '''
    More complete information on a given Linux Distribution

    Can and should include all the software packages that ship with the distro,
    so that an analysis can be made on whether a given package that may be
    responsible for a regression is part of the official set or an external
    package.
    '''

    def __init__(self, name, version, release, arch):
        super(DistroDef, self).__init__(name, version, release, arch)

        #: All the software packages that ship with this Linux distro
        self.software_packages = []

        #: A simple text that denotes the software type that makes this distro
        self.software_packages_type = 'unknown'

    def to_dict(self):
        '''
        Returns the representation as a dictionary
        '''
        d = {'name': self.name,
             'version': self.version,
             'release': self.release,
             'arch': self.arch,
             'software_packages_type': self.software_packages_type,
             'software_packages': []}

        for package in self.software_packages:
            d['software_packages'].append(package.to_dict())

        return d

    def to_json(self):
        '''
        Returns the representation of the distro as JSON
        '''
        return json.dumps(self.to_dict())


class DistroOptions(plugin.Plugin):

    """
    Implements the avocado 'distro' subcommand
    """

    name = 'distro'
    enabled = True

    def configure(self, parser):
        self.parser = parser.subcommands.add_parser(
            'distro',
            help='Shows detected Linux distribution')
        super(DistroOptions, self).configure(self.parser)

    def run(self, args):
        view = output.View()
        detected = distro_utils.detect()
        msg = 'Detected distribution: %s (%s) version %s release %s' % (
            detected.name,
            detected.arch,
            detected.version,
            detected.release)
        view.notify(event="message", msg=msg)
