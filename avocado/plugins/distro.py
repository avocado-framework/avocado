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

import os
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


class DistroPkgInfoLoader(object):

    '''
    Loads information from the distro installation tree into a DistroDef

    It will go through all package files and inspect them with specific
    package utilities, collecting the necessary information.
    '''

    def __init__(self, path):
        self.path = path

    def get_packages_info(self):
        '''
        This method will go throught each file, checking if it's a valid
        software package file by calling :meth:`is_software_package` and
        calling :meth:`load_package_info` if it's so.
        '''
        packages_info = set()
        for dirpath, dirnames, filenames in os.walk(self.path):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                if self.is_software_package(path):
                    packages_info.add(self.get_package_info(path))

        # because we do not track of locations or how many copies of a given
        # package file exists in the installation tree, packages should be
        # comprised of unique entries
        return list(packages_info)

    def is_software_package(self, path):
        '''
        Determines if the given file at `path` is a software package

        This check will be used to determine if :meth:`load_package_info`
        will be called for file at `path`. This method should be
        implemented by classes inheriting from :class:`DistroPkgInfoLoader` and
        could be as simple as checking for a file suffix.

        :param path: path to the software package file
        :type path: str
        :return: either True if the file is a valid software package or False
                 otherwise
        :rtype: bool
        '''
        raise NotImplementedError

    def get_package_info(self, path):
        '''
        Returns information about a given software package

        Should be implemented by classes inheriting from
        :class:`DistroDefinitionLoader`.

        :param path: path to the software package file
        :type path: str
        :returns: tuple with name, version, release, checksum and arch
        :rtype: tuple
        '''
        raise NotImplementedError


#: the type of distro that will determine what loader will be used
DISTRO_PKG_INFO_LOADERS = {}


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
