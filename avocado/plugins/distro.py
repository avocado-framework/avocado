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
import logging
import os
import sys

from avocado.core import exit_codes
from avocado.utils import distro as utils_distro
from avocado.utils import path as utils_path
from avocado.utils import process

from .base import CLICmd


class SoftwarePackage(object):

    """
    Definition of relevant information on a software package
    """

    def __init__(self, name, version, release, checksum, arch):
        self.name = name
        self.version = version
        self.release = release
        self.checksum = checksum
        self.arch = arch

    def to_dict(self):
        """
        Returns the representation as a dictionary
        """
        return {'name': self.name,
                'version': self.version,
                'release': self.release,
                'checksum': self.checksum,
                'arch': self.arch}

    def to_json(self):
        """
        Returns the representation of the distro as JSON
        """
        return json.dumps(self.to_dict())


class DistroDef(utils_distro.LinuxDistro):

    """
    More complete information on a given Linux Distribution

    Can and should include all the software packages that ship with the distro,
    so that an analysis can be made on whether a given package that may be
    responsible for a regression is part of the official set or an external
    package.
    """

    def __init__(self, name, version, release, arch):
        super(DistroDef, self).__init__(name, version, release, arch)

        #: All the software packages that ship with this Linux distro
        self.software_packages = []

        #: A simple text that denotes the software type that makes this distro
        self.software_packages_type = 'unknown'

    def to_dict(self):
        """
        Returns the representation as a dictionary
        """
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
        """
        Returns the representation of the distro as JSON
        """
        return json.dumps(self.to_dict())


class DistroPkgInfoLoader(object):

    """
    Loads information from the distro installation tree into a DistroDef

    It will go through all package files and inspect them with specific
    package utilities, collecting the necessary information.
    """

    def __init__(self, path):
        self.path = path

    def get_packages_info(self):
        """
        This method will go through each file, checking if it's a valid
        software package file by calling :meth:`is_software_package` and
        calling :meth:`load_package_info` if it's so.
        """
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
        """
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
        """
        raise NotImplementedError

    def get_package_info(self, path):
        """
        Returns information about a given software package

        Should be implemented by classes inheriting from
        :class:`DistroDefinitionLoader`.

        :param path: path to the software package file
        :type path: str
        :returns: tuple with name, version, release, checksum and arch
        :rtype: tuple
        """
        raise NotImplementedError


class DistroPkgInfoLoaderRpm(DistroPkgInfoLoader):

    """
    Loads package information for RPM files
    """

    def __init__(self, path):
        super(DistroPkgInfoLoaderRpm, self).__init__(path)
        try:
            utils_path.find_command('rpm')
            self.capable = True
        except utils_path.CmdNotFoundError:
            self.capable = False

    def is_software_package(self, path):
        """
        Systems needs to be able to run the rpm binary in order to fetch
        information on package files. If the rpm binary is not available
        on this system, we simply ignore the rpm files found
        """
        return self.capable and path.endswith('.rpm')

    def get_package_info(self, path):
        cmd = "rpm -qp --qf '%{NAME} %{VERSION} %{RELEASE} %{SIGMD5} %{ARCH}' "
        cmd += path
        info = process.system_output(cmd, ignore_status=True)
        info = tuple(info.split(' '))
        return info


class DistroPkgInfoLoaderDeb(DistroPkgInfoLoader):

    """
    Loads package information for DEB files
    """

    def __init__(self, path):
        super(DistroPkgInfoLoaderDeb, self).__init__(path)
        try:
            utils_path.find_command('dpkg-deb')
            self.capable = True
        except utils_path.CmdNotFoundError:
            self.capable = False

    def is_software_package(self, path):
        return self.capable and (path.endswith('.deb') or
                                 path.endswith('.udeb'))

    def get_package_info(self, path):
        cmd = ("dpkg-deb --showformat '${Package} ${Version} ${Architecture}' "
               "--show ")
        cmd += path
        info = process.system_output(cmd, ignore_status=True)
        name, version, arch = info.split(' ')
        return (name, version, '', '', arch)


#: the type of distro that will determine what loader will be used
DISTRO_PKG_INFO_LOADERS = {'rpm': DistroPkgInfoLoaderRpm,
                           'deb': DistroPkgInfoLoaderDeb}


def save_distro(linux_distro, path):
    """
    Saves the linux_distro to an external file format

    :param linux_distro: an :class:`DistroDef` instance
    :type linux_distro: DistroDef
    :param path: the location for the output file
    :type path: str
    :return: None
    """
    with open(path, 'w') as output:
        output.write(bz2.compress(linux_distro.to_json()))


def load_distro(path):
    """
    Loads the distro from an external file

    :param path: the location for the input file
    :type path: str
    :return: a dict with the distro definition data
    :rtype: dict
    """
    return json.loads(bz2.decompress(open(path).read()))


def load_from_tree(name, version, release, arch, package_type, path):
    """
    Loads a DistroDef from an installable tree

    :param name: a short name that precisely distinguishes this Linux
                 Distribution among all others.
    :type name: str
    :param version: the major version of the distribution. Usually this
                    is a single number that denotes a large development
                    cycle and support file.
    :type version: str
    :param release: the release or minor version of the distribution.
                    Usually this is also a single number, that is often
                    omitted or starts with a 0 when the major version
                    is initially release. It's ofter associated with a
                    shorter development cycle that contains incremental
                    a collection of improvements and fixes.
    :type release: str
    :param arch: the main target for this Linux Distribution. It's common
                 for some architectures to ship with packages for
                 previous and still compatible architectures, such as it's
                 the case with Intel/AMD 64 bit architecture that support
                 32 bit code. In cases like this, this should be set to
                 the 64 bit architecture name.
    :type arch: str
    :param package_type: one of the available package info loader types
    :type package_type: str
    :param path: top level directory of the distro installation tree files
    :type path: str
    """
    distro_def = DistroDef(name, version, release, arch)

    loader_class = DISTRO_PKG_INFO_LOADERS.get(package_type, None)
    if loader_class is not None:
        loader = loader_class(path)
        distro_def.software_packages = [SoftwarePackage(*args)
                                        for args in loader.get_packages_info()]
        distro_def.software_packages_type = package_type
    return distro_def


class Distro(CLICmd):

    """
    Implements the avocado 'distro' subcommand
    """

    name = 'distro'
    description = 'Shows detected Linux distribution'

    def configure(self, parser):
        parser = super(Distro, self).configure(parser)
        parser.add_argument('--distro-def-create',
                            action='store_true', default=False,
                            help=('Creates a distro definition file '
                                  'based on the path given'))
        parser.add_argument('--distro-def-name',
                            help='Distribution short name')
        parser.add_argument('--distro-def-version',
                            help='Distribution major version number')
        parser.add_argument('---distro-def-release', default='',
                            help='Distribution release version number')
        parser.add_argument('--distro-def-arch',
                            help=('Primary architecture that the distro '
                                  'targets'))
        parser.add_argument('--distro-def-path',
                            help=('Top level directory of the distro '
                                  'installation files'))
        type_choices = DISTRO_PKG_INFO_LOADERS.keys()
        type_choices_hlp = ', '.join(type_choices)
        type_help_msg = 'Distro type (one of: %s)' % type_choices_hlp
        parser.add_argument('--distro-def-type', choices=type_choices,
                            help=type_help_msg)

    def get_output_file_name(self, args):
        """
        Adapt the output file name based on given args

        It's not uncommon for some distros to not have a release number, so
        adapt the output file name to that
        """
        if args.distro_def_release:
            return '%s-%s.%s-%s.distro' % (args.distro_def_name,
                                           args.distro_def_version,
                                           args.distro_def_release,
                                           args.distro_def_arch)
        else:
            return '%s-%s-%s.distro' % (args.distro_def_name,
                                        args.distro_def_version,
                                        args.distro_def_arch)

    def run(self, args):
        log = logging.getLogger("avocado.app")
        if args.distro_def_create:
            if not (args.distro_def_name and args.distro_def_version and
                    args.distro_def_arch and args.distro_def_type and
                    args.distro_def_path):
                log.error('Required arguments: name, version, arch, type '
                          'and path')
                sys.exit(exit_codes.AVOCADO_FAIL)

            output_file_name = self.get_output_file_name(args)
            if os.path.exists(output_file_name):
                error_msg = ('Output file "%s" already exists, will not '
                             'overwrite it', output_file_name)
                log.error(error_msg)
            else:
                log.debug("Loading distro information from tree... "
                          "Please wait...")
                distro = load_from_tree(args.distro_def_name,
                                        args.distro_def_version,
                                        args.distro_def_release,
                                        args.distro_def_arch,
                                        args.distro_def_type,
                                        args.distro_def_path)
                save_distro(distro, output_file_name)
                log.debug('Distro information saved to "%s"',
                          output_file_name)
        else:
            detected = utils_distro.detect()
            log.debug('Detected distribution: %s (%s) version %s release %s',
                      detected.name, detected.arch, detected.version,
                      detected.release)
