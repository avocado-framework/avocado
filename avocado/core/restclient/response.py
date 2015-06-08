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

"""
Module with base model functions to manipulate JSON data
"""

import json


class InvalidJSONError(Exception):

    """
    Data given to a loader/decoder is not valid JSON
    """
    pass


class InvalidResultResponseError(Exception):

    """
    Returned result response does not conform to expectation

    Even though the result may be a valid json, it may not have the required
    or expected information that would normally be sent by avocado-server.
    """
    pass


class BaseResponse(object):

    """
    Base class that provides commonly used features for response handling
    """

    REQUIRED_DATA = []

    def __init__(self, json_data):
        self._json_data = json_data
        self._data = None
        self._load_data()

    def _parse_data(self):
        try:
            self._data = json.loads(self._json_data)
        except ValueError:
            raise InvalidJSONError(self._json_data)

    def _load_data(self):
        self._parse_data()

        if self.REQUIRED_DATA:
            missing_data = []
            for data_member in self.REQUIRED_DATA:
                if data_member not in self._data:
                    missing_data.append(data_member)
            if missing_data:
                missing = ", ".join(missing_data)
                msg = "data member(s) missing from response: %s" % missing
                raise InvalidResultResponseError(msg)


class ResultResponse(BaseResponse):

    """
    Provides a wrapper around an ideal result response

    This class should be instantiated with the JSON data received from an
    avocado-server, and will check if the required data members are present
    and thus the response is well formed.
    """

    REQUIRED_DATA = ['count', 'next', 'previous', 'results']

    def __init__(self, json_data):
        self.count = 0
        self.next = None
        self.previous = None
        self.results = []
        super(ResultResponse, self).__init__(json_data)

    def _load_data(self):
        super(ResultResponse, self)._load_data()
        self.count = self._data.get('count')
        self.next = self._data.get('next')
        self.previous = self._data.get('previous')
        self.results = self._data.get('results')
