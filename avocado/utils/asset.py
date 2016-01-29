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
import tempfile
import urlparse

from . import crypto
from . import download
from . import path as utils_path


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
        :param algorithm: hash algorithm (default sha1)
        :param locations: list of locations fetch asset from
        """
        self.name = name
        self.asset_hash = asset_hash
        self.algorithm = algorithm
        self.locations = locations
        self.cache_dirs = cache_dirs
        self.path = self.fetch()

    def fetch(self):
        urls = []
        nameobj = urlparse.urlparse(self.name)
        self.basename = os.path.basename(nameobj.path)

        # If name is actually an url, it has to be included in urls list
        if nameobj.scheme:
            urls.append(nameobj.geturl())

        # First let's find for the file in all cache locations
        for cache_dir in self.cache_dirs:
            cache_dir = os.path.expanduser(cache_dir)
            self.asset_file = os.path.join(cache_dir, self.basename)
            if self._check_file():
                return self.asset_file

        # If we get to this point, file is not in any cache directory
        # and we have to download it from a location. A rw cache
        # directory is then needed. The first rw cache directory will be
        # used.
        for cache_dir in self.cache_dirs:
            cache_dir = os.path.expanduser(cache_dir)
            self.asset_file = os.path.join(cache_dir, self.basename)
            if not self._writable(cache_dir):
                log.debug("Read-only cache dir '%s'. Skiping." %
                          cache_dir)
                continue

            # Adding the user defined locations to the urls list
            if self.locations is not None:
                for item in self.locations:
                    urls.append(item)

            for url in urls:
                urlobj = urlparse.urlparse(url)
                if urlobj.scheme == 'http':
                    log.debug('Downloading from %s.' % url)
                    try:
                        download._get_file(url, self.asset_file)
                    except Exception as e:
                        log.error(e)
                        continue
                    if self._check_file():
                        return self.asset_file

                elif urlobj.scheme == 'ftp':
                    log.debug('Downloading from %s.' % url)
                    try:
                        download._get_file(url, self.asset_file)
                    except Exception as e:
                        log.error(e)
                        continue
                    if self._check_file():
                        return self.asset_file

                elif urlobj.scheme == 'file':
                    log.debug('Copying from %s.' % urlobj.path)
                    if os.path.isdir(urlobj.path):
                        path = os.path.join(urlobj.path, self.name)
                    else:
                        path = urlobj.path
                    try:
                        download._get_file(path, self.asset_file)
                    except Exception as e:
                        log.error(e)
                        continue
                    if self._check_file():
                        return self.asset_file

        raise EnvironmentError("Failed to fetch %s." % self.basename)

    def _check_file(self):
        """
        Checks if file exists and verifies the hash, when the hash is
        provided. We try first to find a hash file to verify the hash
        against and only if the hash file is not present we compute the
        hash.
        """
        if not os.path.isfile(self.asset_file):
            log.debug('Asset %s not found.' % self.asset_file)
            return False

        if self.asset_hash is None:
            log.debug('Skipping hash check for %s.' % self.asset_file)
            return True

        discovered_hash = None
        # Try to find a hashfile for the asset file
        hashfile = '.'.join([self.asset_file, self.algorithm])
        if os.path.isfile(hashfile):
            with open(hashfile, 'r') as f:
                for line in f.readlines():
                    if self.basename in line:
                        log.debug('Hashfile found for %s.' %
                                  self.asset_file)
                        discovered_hash = line.split()[0]
                        break

        # If no hashfile, lets calculate the hash by ourselves
        if discovered_hash is None:
            log.debug('No hashfile found for %s. Computing hash.' %
                      self.asset_file)
            discovered_hash = crypto.hash_file(self.asset_file,
                                               algorithm=self.algorithm)

            # Creating the hashfile for further usage.
            log.debug('Creating hashfile %s.' % hashfile)
            with open(hashfile, 'w') as f:
                content = ' '.join([discovered_hash, self.basename])
                content += '\n'
                f.write(content)

        if self.asset_hash == discovered_hash:
            log.debug('Asset %s verified.' % self.asset_file)
            return True
        else:
            log.error('Asset %s corrupted (hash expected:%s, hash found:%s).' %
                      (self.asset_file, self.asset_hash, discovered_hash))
            return False

    def _writable(self, directory):
        """
        Checks if a given directory is writable, trying to create it on
        demand.
        """
        if os.path.isdir(directory):
            try:
                fd, path = tempfile.mkstemp(dir=directory)
                os.close(fd)
                os.unlink(path)
                return True
            except OSError:
                pass
        else:
            try:
                utils_path.init_dir(directory)
                return True
            except OSError as e:
                pass
        return False
