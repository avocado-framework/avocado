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
# Authors: Cleber Rosa <cleber@redhat.com>

"""
Test location discovery
"""

import os
import re


class LocationDiscovery(object):

    """
    LocationDiscovery should return a list of locations that may contain tests

    It's not up to LocationDiscovery to inspect each location and come up with
    a list of tests, and not even the type of tests that were found.

    It should, though, for each location root point given, walk through all of
    its possible underlying members, and return a complete list of them, so
    that no further location discovery is necessary.
    """

    #: List of functions to be run on each location. If any function returns
    #: something that evals to True, then the location being checked is included
    INCLUDE_CHECK_FUNCTIONS = [lambda location: True]

    #: List of functions to be run on each location. If any function returns
    #: something that evals to True, then the location being checked is ignored
    IGNORE_CHECK_FUNCTIONS = []

    def __init__(self, root):
        self.root = root

    def filter(self, locations):
        """
        Runs the include and ignore functions to include and exclude locations
        """
        included = []
        for location in locations:
            for check in self.INCLUDE_CHECK_FUNCTIONS:
                if check(location):
                    included.append(location)
        result = []
        for location in included:
            ignored = False
            for check in self.IGNORE_CHECK_FUNCTIONS:
                if check(location):
                    ignored = True
                    continue
            if not ignored:
                result.append(location)
        return result

    def discover(self):
        """
        Performs the actual discovery for possible test locations

        :returns: the locations where may be possible to find tests
        :rtype: list
        """
        raise NotImplementedError

    def get_locations(self):
        """
        Returns a final, filtered version of the discovered locations

        This will run :meth:`discover`, and subsequently will run all locations
        through the :meth:`filter`.

        :rtype: list
        """
        discovered = self.discover()
        locations = self.filter(discovered)
        return locations


class FileLocationDiscovery(LocationDiscovery):

    def discover(self):
        locations = []

        if os.path.isfile(self.root):
            locations.append(self.root)

        elif os.path.isdir(self.root):
            for dirpath, _, filenames in os.walk(self.root):
                for filename in filenames:
                    locations.append(os.path.join(dirpath, filename))

        return locations


class NamedFileLocationDiscovery(FileLocationDiscovery):

    INCLUDE_LOCATION_NAMES = [re.compile('.*')]

    def __init__(self, root):
        super(NamedFileLocationDiscovery, self).__init__(root)
        self.INCLUDE_CHECK_FUNCTIONS = [self._check_location_name]

    def _check_location_name(self, location):
        for regex in self.INCLUDE_LOCATION_NAMES:
            if regex.match(location):
                return True
        return False


class PythonFileLocationDiscovery(NamedFileLocationDiscovery):

    INCLUDE_LOCATION_NAMES = [re.compile('.*\.py$')]


class AccessFileLocationDiscovery(FileLocationDiscovery):

    INCLUDE_MODES = []

    def __init__(self, root):
        super(AccessFileLocationDiscovery, self).__init__(root)
        self.INCLUDE_CHECK_FUNCTIONS = [self._check_access_mode]

    def _check_access_mode(self, location):
        for include_mode in self.INCLUDE_MODES:
            if os.access(location, include_mode):
                return True
        return False


class ReadableExecutableFileLocationDiscovery(AccessFileLocationDiscovery):

    INCLUDE_MODES = [os.R_OK | os.X_OK]
