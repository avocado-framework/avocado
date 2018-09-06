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

import errno
import hashlib
import logging
import os
import re
import shutil
import stat
import sys
import tempfile
import time

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from . import astring
from . import crypto
from . import path as utils_path
from .download import url_download
from .filelock import FileLock


log = logging.getLogger('avocado.test')


#: The default hash algorithm to use on asset cache operations
DEFAULT_HASH_ALGORITHM = 'sha1'


class UnsupportedProtocolError(EnvironmentError):
    """
    Signals that the protocol of the asset URL is not supported
    """


class Asset(object):
    """
    Try to fetch/verify an asset file from multiple locations.
    """

    def __init__(self, name, asset_hash, algorithm, locations, cache_dirs,
                 expire=None):
        """
        Initialize the Asset() class.

        :param name: the asset filename. url is also supported
        :param asset_hash: asset hash
        :param algorithm: hash algorithm
        :param locations: list of locations fetch asset from
        :param cache_dirs: list of cache directories
        :param expire: time in seconds for the asset to expire
        """
        self.name = name
        self.asset_hash = asset_hash
        if algorithm is None:
            self.algorithm = DEFAULT_HASH_ALGORITHM
        else:
            self.algorithm = algorithm
        self.locations = locations
        self.cache_dirs = cache_dirs
        self.expire = expire

    def _get_writable_cache_dir(self):
        """
        Returns the first available writable cache directory

        When a asset has to be downloaded, a writable cache directory
        is then needed. The first available writable cache directory
        will be used.

        :returns: the first writable cache dir
        :rtype: str
        :raises: EnvironmentError
        """
        for cache_dir in self.cache_dirs:
            cache_dir = os.path.expanduser(cache_dir)
            if utils_path.usable_rw_dir(cache_dir):
                return cache_dir
        raise EnvironmentError("Can't find a writable cache directory.")

    @staticmethod
    def _get_hash_file(asset_file):
        """
        Returns the file name that contains the hash for a given asset file
        """
        return '%s-CHECKSUM' % asset_file

    def _get_relative_dir(self, parsed_url):
        """
        When an asset has a name and a hash, there's a clear intention
        for it to be unique *by name*, overwriting it if the file is
        corrupted or expired.  These will be stored in the cache directory
        indexed by name.

        When an asset does not have a hash, they will be saved according
        to their locations, so that multiple assets with the same file name,
        but completely unrelated to each other, will still coexist.
        """
        if self.asset_hash:
            return 'by_name'
        base_url = "%s://%s/%s" % (parsed_url.scheme,
                                   parsed_url.netloc,
                                   os.path.dirname(parsed_url.path))
        base_url_hash = hashlib.new(DEFAULT_HASH_ALGORITHM,
                                    base_url.encode(astring.ENCODING))
        return os.path.join('by_location', base_url_hash.hexdigest())

    def fetch(self):
        """
        Fetches the asset. First tries to find the asset on the provided
        cache_dirs list. Then tries to download the asset from the locations
        list provided.

        :raise EnvironmentError: When it fails to fetch the asset
        :returns: The path for the file on the cache directory.
        """
        urls = []
        parsed_url = urlparse.urlparse(self.name)
        basename = os.path.basename(parsed_url.path)
        cache_relative_dir = self._get_relative_dir(parsed_url)

        # If name is actually an url, it has to be included in urls list
        if parsed_url.scheme:
            urls.append(parsed_url.geturl())

        # First let's search for the file in each one of the cache locations
        for cache_dir in self.cache_dirs:
            cache_dir = os.path.expanduser(cache_dir)
            asset_file = os.path.join(cache_dir, cache_relative_dir, basename)

            # To use a cached file, it must:
            # - Exists.
            # - Be valid (not expired).
            # - Be verified (hash check).
            if (os.path.isfile(asset_file) and
                    not self._is_expired(asset_file, self.expire)):
                try:
                    with FileLock(asset_file, 1):
                        if self._verify(asset_file):
                            return asset_file
                except Exception:
                    exc_type, exc_value = sys.exc_info()[:2]
                    log.error('%s: %s', exc_type.__name__, exc_value)

        # If we get to this point, we have to download it from a location.
        # A writable cache directory is then needed. The first available
        # writable cache directory will be used.
        cache_dir = self._get_writable_cache_dir()
        # Now we have a writable cache_dir. Let's get the asset.
        # Adding the user defined locations to the urls list:
        if self.locations is not None:
            for item in self.locations:
                urls.append(item)

        for url in urls:
            urlobj = urlparse.urlparse(url)
            if urlobj.scheme in ['http', 'https', 'ftp']:
                fetch = self._download
            elif urlobj.scheme == 'file':
                fetch = self._get_local_file
            else:
                raise UnsupportedProtocolError("Unsupported protocol"
                                               ": %s" % urlobj.scheme)
            cache_relative_dir = self._get_relative_dir(urlobj)
            asset_file = os.path.join(cache_dir, cache_relative_dir, basename)
            dirname = os.path.dirname(asset_file)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            try:
                if fetch(urlobj, asset_file):
                    return asset_file
            except Exception:
                exc_type, exc_value = sys.exc_info()[:2]
                log.error('%s: %s', exc_type.__name__, exc_value)

        raise EnvironmentError("Failed to fetch %s." % basename)

    def _download(self, url_obj, asset_file):
        try:
            # Temporary unique name to use while downloading
            temp = '%s.%s' % (asset_file,
                              next(tempfile._get_candidate_names()))
            url_download(url_obj.geturl(), temp)

            # Acquire lock only after download the file
            with FileLock(asset_file, 1):
                shutil.copy(temp, asset_file)
                self._compute_hash(asset_file)
                return self._verify(asset_file)
        finally:
            os.remove(temp)

    def _compute_hash(self, asset_file):
        result = crypto.hash_file(asset_file, algorithm=self.algorithm)
        with open(self._get_hash_file(asset_file), 'w') as f:
            f.write('%s %s\n' % (self.algorithm, result))

    def _get_hash_from_file(self, asset_file):
        discovered = None
        hash_file = self._get_hash_file(asset_file)
        if not os.path.isfile(hash_file):
            self._compute_hash(asset_file)

        with open(hash_file, 'r') as hash_file:
            for line in hash_file:
                # md5 is 32 chars big and sha512 is 128 chars big.
                # others supported algorithms are between those.
                pattern = '%s [a-f0-9]{32,128}' % self.algorithm
                if re.match(pattern, line):
                    discovered = line.split()[1]
                    break
        return discovered

    def _verify(self, asset_file):
        if not self.asset_hash:
            return True
        if self._get_hash_from_file(asset_file) == self.asset_hash:
            return True
        else:
            return False

    def _get_local_file(self, url_obj, asset_file):
        if os.path.isdir(url_obj.path):
            path = os.path.join(url_obj.path, self.name)
        else:
            path = url_obj.path

        try:
            with FileLock(asset_file, 1):
                try:
                    os.symlink(path, asset_file)
                    self._compute_hash(asset_file)
                    return self._verify(asset_file)
                except OSError as detail:
                    if detail.errno == errno.EEXIST:
                        os.remove(asset_file)
                        os.symlink(path, asset_file)
                        self._compute_hash(asset_file)
                        return self._verify(asset_file)
        except:
            raise

    @staticmethod
    def _is_expired(path, expire):
        if expire is None:
            return False
        creation_time = os.lstat(path)[stat.ST_CTIME]
        expire_time = creation_time + expire
        if time.time() > expire_time:
            return True
        return False
