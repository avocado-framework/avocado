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

from .settings import settings
from ..utils import crypto
from ..utils import download


log = logging.getLogger('avocado.test')


class Asset(object):
    """
    Try to fetch/verify an asset file from multiple locations.
    """

    def __init__(self, name, asset_hash, algorithm, locations, cache):
        self.name = name
        self.asset_hash = asset_hash
        self.algorithm = algorithm
        self.locations = locations
        self.cache_dir = os.path.expanduser(settings.get_value('datadir.paths',
                                            'cache_dir', default=cache))
        if not os.path.exists(self.cache_dir):
            os.mkdir(self.cache_dir)
        self.path = self.fetch()

    def fetch(self):
        urls = []
        nameobj = urlparse.urlparse(self.name)
        self.basename = os.path.basename(nameobj.path)
        self.asset_file = os.path.join(self.cache_dir, self.basename)

        if self._check_file():
            return self.asset_file

        # If name is actually an url, it has to be included in urls list
        if nameobj.scheme:
            urls.append(nameobj.geturl())

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
        if not os.path.isfile(self.asset_file):
            log.debug('Asset %s not found.' % self.asset_file)
            return False

        if self.asset_hash is None:
            log.debug('Skipping hash check for %s.' % self.asset_file)
            return True

        discovered_hash = None
        # Try to find a hashfile for the self.asset_file
        hash_extensions = ['md5', 'md5sum', 'sha1', 'sha1sum']
        for hash_extension in hash_extensions:
            search = '.'.join([self.asset_file, hash_extension])
            if os.path.isfile(search):
                with open(search, 'r') as f:
                    for line in f.readlines():
                        if self.basename in line:
                            log.debug('hashfile found for %s.' %
                                      self.asset_file)
                            discovered_hash = line.split()[0]
                            break

        # If no hashfile, lets calculate the hash by ourselves
        if discovered_hash is None:
            log.debug('No hashfile found for %s. Computing hash.' %
                      self.asset_file)
            discovered_hash = crypto.hash_file(self.asset_file,
                                               algorithm=self.algorithm)
            hash_filename = '.'.join([self.asset_file, self.algorithm])
            log.debug('Creating hashfile %s.' % hash_filename)
            with open(hash_filename, 'w') as f:
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
