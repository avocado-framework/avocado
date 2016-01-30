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
Asset fetcher from multiple locations

"""

import logging
import os
import urlparse

from . import crypto
from . import download


log = logging.getLogger('avocado.test')


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


def fetch(self, search='asset'):
    """
    Tries to fetch a file from multiple locations, trying the cache
    first and caching when successfully fetched.

    Expected yaml format:

    asset:
        name: <name> # Not null
        md5sum: <hash> # Optional. Skips the check if null.
        cache_dir: <path> # Optional. Default is test temporary dir.
        location: # list of locations to try.
        - file://<path>
        - http://<url>
        - ftp://<url>

    :param self: avocado test self instance.
    :param search: (optional) search for yaml option with all the asset
            data. Default is 'asset'.
    :return: asset path.
    """

    name = self.params.get('name', '*/%s/*' % search, default=None)
    md5sum = self.params.get('md5sum', '*/%s/*' % search, default=None)
    cache_dir = self.params.get('cache_dir', '*/%s/*' % search,
                                default=self.workdir)
    location = self.params.get('location', '*/%s/*' % search, default=None)

    dst = os.path.join(cache_dir, name)
    if name is None:
        log.error('Asset name is missing.')
        return None
    if _check_file(dst, md5sum):
        return dst
    if location is None:
        return None

    for url in location:
        urlobj = urlparse.urlparse(url)
        if urlobj.scheme == 'http':
            log.debug('Trying to download from %s.' % url)
            try:
                download._get_file(url, dst)
            except Exception as e:
                log.error(e)
                continue
            if _check_file(dst, md5sum):
                return dst

        elif urlobj.scheme == 'ftp':
            log.debug('Trying to download from %s.' % url)
            try:
                download._get_file(url, dst)
            except Exception as e:
                log.error(e)
                continue
            if _check_file(dst, md5sum):
                return dst

        elif urlobj.scheme == 'file':
            log.debug('Trying to copy from %s.' % urlobj.path)
            try:
                download._get_file(urlobj.path, dst)
            except Exception as e:
                log.error(e)
                continue
            if _check_file(dst, md5sum):
                return dst

    log.error('No more locations to try.')
    return None
