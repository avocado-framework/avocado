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
This module provides connection classes the avocado server.

A connection is a simple wrapper around a HTTP request instance. It is this
basic object that allows methods to be called on the remote server.
"""

import requests

from ..settings import settings


__all__ = ['get_default', 'Connection']


#: Minimum required version of server side API
MIN_REQUIRED_VERSION = (0, 2, 0)


class InvalidConnectionError(Exception):

    """
    Invalid connection for selected server
    """
    pass


class InvalidServerVersionError(Exception):

    """
    The server version does not satisfy the minimum required version
    """
    pass


class UnexpectedHttpStatusCode(Exception):

    """
    Server has returned a response with a status code different than expected
    """

    def __init__(self, expected, received):
        self.expected = expected
        self.received = received

    def __str__(self):
        msg = "Unexpected HTTP response status: expected %s, received %s"
        return msg % (self.expected, self.received)


class Connection(object):

    """
    Connection to the avocado server
    """

    def __init__(self, hostname=None, port=None, username=None, password=None):
        """
        Initializes a connection to an avocado-server instance

        :param hostname: the hostname or IP address to connect to
        :type hostname: str
        :param port: the port number where avocado-server is running
        :type port: int
        :param username: the name of the user to be authenticated as
        :type username: str
        :param password: the password to use for authentication
        :type password: str
        """
        if hostname is None:
            hostname = settings.get_value('restclient.connection',
                                          'hostname', default='localhost')
        self.hostname = hostname

        if port is None:
            port = settings.get_value('restclient.connection',
                                      'port', key_type='int',
                                      default=9405)
        self.port = port

        if username is None:
            username = settings.get_value('restclient.connection',
                                          'username', default='')
        self.username = username

        if password is None:
            password = settings.get_value('restclient.connection',
                                          'password', default='')
        self.password = password

        try:
            version = self.request('version')
        except (requests.exceptions.ConnectionError, UnexpectedHttpStatusCode):
            raise InvalidConnectionError

        if not self.check_min_version(version):
            raise InvalidServerVersionError

    def get_url(self, path=None):
        """
        Returns a representation of the current connection as an HTTP URL
        """
        if path is None:
            return 'http://%s:%s' % (self.hostname, self.port)

        return 'http://%s:%s/%s' % (self.hostname, self.port, path)

    def request(self, path, method=requests.get, check_status=True, **data):
        """
        Performs a request to the server

        This method is heavily used by upper level API methods, and more often
        than not, those upper level API methods should be used instead.

        :param path: the path on the server where the resource lives
        :type path: str
        :param method: the method you want to call on the remote server,
                       defaults to a HTTP GET
        :param check_status: whether to check the HTTP status code that comes
                             with the response. If set to `True`, it will
                             depend on the method chosen. If set to `False`,
                             no check will be performed. If an integer is given
                             then that specific status will be checked for.
        :param data: keyword arguments to be passed to the remote method
        :returns: JSON data
        """
        url = self.get_url(path)

        if self.username and self.password:
            response = method(url,
                              auth=(self.username, self.password),
                              params=data)
        else:
            response = method(url, params=data)

        want_status = None
        if check_status is True:
            if method == requests.get:
                want_status = 200
            elif method == requests.post:
                want_status = 201
            elif method == requests.delete:
                want_status = 204

        if want_status is not None:
            if response.status_code != want_status:
                raise UnexpectedHttpStatusCode(want_status,
                                               response.status_code)

        return response.json()

    def check_min_version(self, data=None):
        """
        Checks the minimum server version
        """
        if data is None:
            response = self.request('version')
            version = response.get('version')
            if version is None:
                return False
        else:
            version = data.get('version')

        major, minor, release = version.split('.', 3)
        version = (int(major), int(minor), int(release))
        return MIN_REQUIRED_VERSION >= version

    def ping(self):
        """
        Tests connectivity to the currently set avocado-server

        This is intentionally a simple method that will only return True if a
        request is made, and a response is received from the server.
        """
        try:
            self.request('version')
        except Exception:
            return False
        return True

    def get_api_list(self):
        """
        Gets the list of APIs the server makes available to the current user
        """
        return self.request('')


#: Global, default connection for ease of use by apps
CONNECTION = None


def get_default():
    """
    Returns the global, default connection to avocado-server

    :returns: an avocado.core.restclient.connection.Connection instance
    """
    global CONNECTION

    if CONNECTION is None:
        CONNECTION = Connection()

    return CONNECTION
