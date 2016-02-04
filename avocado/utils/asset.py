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
# Copyright: Red Hat Inc. 2016
# Author: Amador Pahim <apahim@redhat.com>

"""
Asset fetcher from multiple locationss

"""

import logging
import os
import urlparse

from . import crypto
from . import download


log = logging.getLogger('avocado.test')


class Asset(object):
    """
    Try to fetch/verify an asset file from multiple locations.
    """

    def __init__(self,
                 name=None,
                 cache_dir=None,
                 md5sum=None,
                 locations=[]):
        self.name = name
        self.md5sum = md5sum
        self.cache_dir = cache_dir
        self.locations = locations

    def fetch(self):
        if self.name is None:
            log.error('Asset name is missing.')
            return None
        if self.cache_dir is None:
            log.error('Asset cache_dir is missing.')
            return None

        dst = os.path.join(self.cache_dir, self.name)
        if self._check_file(dst, self.md5sum):
            return dst

        if not isinstance(self.locations, list):
            log.error("'locations' must be a list.")
            return None

        for url in self.locations:
            urlobj = urlparse.urlparse(url)
            if urlobj.scheme == 'http':
                log.debug('Downloading from %s.' % url)
                try:
                    download._get_file(url, dst)
                except Exception as e:
                    log.error(e)
                    continue
                if self._check_file(dst, self.md5sum):
                    return dst

            elif urlobj.scheme == 'ftp':
                log.debug('Downloading from %s.' % url)
                try:
                    download._get_file(url, dst)
                except Exception as e:
                    log.error(e)
                    continue
                if self._check_file(dst, self.md5sum):
                    return dst

            elif urlobj.scheme == 'file':
                log.debug('Copying from %s.' % urlobj.path)
                if os.path.isdir(urlobj.path):
                    path = os.path.join(urlobj.path, self.name)
                else:
                    path = urlobj.path
                try:
                    download._get_file(path, dst)
                except Exception as e:
                    log.error(e)
                    continue
                if self._check_file(dst, self.md5sum):
                    return dst

        log.error('No more locations to try.')
        return None

    @staticmethod
    def _check_file(filename, expected_hash):
        if not os.path.isfile(filename):
            log.error('Asset %s not found.' % filename)
            return False

        if expected_hash is None:
            log.debug('Skipping hash check for %s.' % filename)
            return True

        file_hash = crypto.hash_file(filename)
        if file_hash == expected_hash:
            log.debug('Asset %s verified.' % filename)
            return True
        else:
            log.error('Asset %s corrupted.' % filename)
            return False
