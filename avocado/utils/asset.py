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
import re
import urlparse

from . import crypto
from . import path as utils_path
from .download import url_download


log = logging.getLogger('avocado.test')


class Asset(object):
    """
    Try to fetch/verify an asset file from multiple locations.
    """

    def __init__(self, name, asset_hash, algorithm, locations, cache_dirs):
        """
        Initialize the Asset() and fetches the asset file. The path for
        the fetched file can be reached using the self.path attribute.

        :param name: the asset filename. url is also supported
        :param asset_hash: asset hash
        :param algorithm: hash algorithm
        :param locations: list of locations fetch asset from
        :params cache_dirs: list of cache directories
        """
        self.name = name
        self.asset_hash = asset_hash
        self.algorithm = algorithm
        self.locations = locations
        self.cache_dirs = cache_dirs
        self.nameobj = urlparse.urlparse(self.name)
        self.basename = os.path.basename(self.nameobj.path)

    def fetch(self):
        urls = []

        # If name is actually an url, it has to be included in urls list
        if self.nameobj.scheme:
            urls.append(self.nameobj.geturl())

        # First let's find for the file in all cache locations
        for cache_dir in self.cache_dirs:
            cache_dir = os.path.expanduser(cache_dir)
            self.asset_file = os.path.join(cache_dir, self.basename)
            if self._check_file(self.asset_file, self.asset_hash, self.algorithm):
                return self.asset_file

        # If we get to this point, file is not in any cache directory
        # and we have to download it from a location. A rw cache
        # directory is then needed. The first rw cache directory will be
        # used.
        log.debug("Looking for a writable cache dir.")
        for cache_dir in self.cache_dirs:
            cache_dir = os.path.expanduser(cache_dir)
            self.asset_file = os.path.join(cache_dir, self.basename)
            if not utils_path.usable_rw_dir(cache_dir):
                log.debug("Read-only cache dir '%s'. Skiping." %
                          cache_dir)
                continue
            log.debug("Using %s as cache dir." % cache_dir)

            # Adding the user defined locations to the urls list
            if self.locations is not None:
                for item in self.locations:
                    urls.append(item)

            for url in urls:
                urlobj = urlparse.urlparse(url)
                if urlobj.scheme == 'http' or urlobj.scheme == 'https':
                    log.debug('Downloading from %s.' % url)
                    try:
                        url_download(url, self.asset_file)
                    except Exception as e:
                        log.error(e)
                        continue
                    if self._check_file(self.asset_file, self.asset_hash,
                                        self.algorithm):
                        return self.asset_file

                elif urlobj.scheme == 'ftp':
                    log.debug('Downloading from %s.' % url)
                    try:
                        url_download(url, self.asset_file)
                    except Exception as e:
                        log.error(e)
                        continue
                    if self._check_file(self.asset_file, self.asset_hash,
                                        self.algorithm):
                        return self.asset_file

                elif urlobj.scheme == 'file':
                    if os.path.isdir(urlobj.path):
                        path = os.path.join(urlobj.path, self.name)
                    else:
                        path = urlobj.path
                    log.debug('Looking for file on %s.' % path)
                    if self._check_file(path):
                        os.symlink(path, self.asset_file)
                        log.debug('Symlink created %s -> %s.' %
                                  (self.asset_file, path))
                    else:
                        continue
                    if self._check_file(self.asset_file, self.asset_hash,
                                        self.algorithm):
                        return self.asset_file

            raise EnvironmentError("Failed to fetch %s." % self.basename)
        raise EnvironmentError("Can't find a writable cache dir.")

    @staticmethod
    def _check_file(path, filehash=None, algorithm=None):
        """
        Checks if file exists and verifies the hash, when the hash is
        provided. We try first to find a hash file to verify the hash
        against and only if the hash file is not present we compute the
        hash.
        """
        if not os.path.isfile(path):
            log.debug('Asset %s not found.' % path)
            return False

        if filehash is None:
            return True

        basename = os.path.basename(path)
        discovered_hash = None
        # Try to find a hashfile for the asset file
        hashfile = '%s.%s' % (path, algorithm)
        if os.path.isfile(hashfile):
            with open(hashfile, 'r') as f:
                for line in f.readlines():
                    # md5 is 32 chars big and sha512 is 128 chars big.
                    # others supported algorithms are between those.
                    pattern = '[a-f0-9]{32,128} %s' % basename
                    if re.match(pattern, line):
                        log.debug('Hashfile found for %s.' % path)
                        discovered_hash = line.split()[0]
                        break

        # If no hashfile, lets calculate the hash by ourselves
        if discovered_hash is None:
            log.debug('No hashfile found for %s. Computing hash.' %
                      path)
            discovered_hash = crypto.hash_file(path, algorithm=algorithm)

            # Creating the hashfile for further usage.
            log.debug('Creating hashfile %s.' % hashfile)
            with open(hashfile, 'w') as f:
                content = '%s %s\n' % (discovered_hash, basename)
                f.write(content)

        if filehash == discovered_hash:
            log.debug('Asset %s verified.' % path)
            return True
        else:
            log.error('Asset %s corrupted (hash expected:%s, hash found:%s).' %
                      (path, filehash, discovered_hash))
            return False
