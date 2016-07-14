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
import logging
import os
import re
import shutil
import stat
import sys
import time
import tempfile
import urlparse

from . import crypto
from . import filelock
from . import path as utils_path
from .download import url_download


log = logging.getLogger('avocado.test')


class Asset(object):
    """
    Try to fetch/verify an asset file from multiple locations.
    """

    def __init__(self, name, asset_hash, algorithm, locations, cache_dirs,
                 expire):
        """
        Initialize the Asset() class.

        :param name: the asset filename. url is also supported
        :param asset_hash: asset hash
        :param algorithm: hash algorithm
        :param locations: list of locations fetch asset from
        :params cache_dirs: list of cache directories
        :params expire: time in seconds for the asset to expire
        """
        self.name = name
        self.asset_hash = asset_hash
        if algorithm is None:
            self.algorithm = 'sha1'
        else:
            self.algorithm = algorithm
        self.locations = locations
        self.cache_dirs = cache_dirs
        self.nameobj = urlparse.urlparse(self.name)
        self.basename = os.path.basename(self.nameobj.path)
        self.expire = expire

    def fetch(self):
        """
        Fetches the asset. First tries to find the asset on the provided
        cache_dirs list. Then tries to download the asset from the locations
        list provided.

        :returns: The path for the file on the cache directory.
        """
        urls = []

        # If name is actually an url, it has to be included in urls list
        if self.nameobj.scheme:
            urls.append(self.nameobj.geturl())

        # First let's find for the file in all cache locations
        for cache_dir in self.cache_dirs:
            cache_dir = os.path.expanduser(cache_dir)
            self.asset_file = os.path.join(cache_dir, self.basename)
            self.hashfile = '%s-CHECKSUM' % self.asset_file

            # To use a cached file, it must:
            # - Exists.
            # - Be valid (not expired).
            # - Be verified (hash check).
            if (os.path.isfile(self.asset_file) and
               not self._is_expired(self.asset_file, self.expire)):
                lock = filelock.LockFile(self.asset_file, timeout=1)
                try:
                    lock.acquire()
                    if self._verify():
                        return self.asset_file
                except:
                    exc_type, exc_value = sys.exc_info()[:2]
                    log.error('%s: %s' % (exc_type.__name__, exc_value))
                finally:
                    lock.release()

        # If we get to this point, we have to download it from a location.
        # A writable cache directory is then needed. The first available
        # writable cache directory will be used.
        for cache_dir in self.cache_dirs:
            cache_dir = os.path.expanduser(cache_dir)
            self.asset_file = os.path.join(cache_dir, self.basename)
            if not utils_path.usable_rw_dir(cache_dir):
                continue

            # Now we have a writable cache_dir. Let's get the asset.
            # Adding the user defined locations to the urls list:
            if self.locations is not None:
                for item in self.locations:
                    urls.append(item)

            for url in urls:
                urlobj = urlparse.urlparse(url)
                if urlobj.scheme in ['http', 'https', 'ftp']:
                    try:
                        if self._download(url):
                            return self.asset_file
                    except:
                        exc_type, exc_value = sys.exc_info()[:2]
                        log.error('%s: %s' % (exc_type.__name__, exc_value))

                elif urlobj.scheme == 'file':
                    # Being flexible with the urlparse result
                    if os.path.isdir(urlobj.path):
                        path = os.path.join(urlobj.path, self.name)
                    else:
                        path = urlobj.path

                    try:
                        if self._get_local_file(path):
                            return self.asset_file
                    except:
                        exc_type, exc_value = sys.exc_info()[:2]
                        log.error('%s: %s' % (exc_type.__name__, exc_value))

            # Despite our effort, we could not provide a healthy file. Sorry.
            log.error("Failed to fetch %s." % self.basename)
            return None

        # Cannot find a writable cache_dir. Bye.
        log.error("Can't find a writable cache dir.")
        return None

    def _download(self, url):
        lock = filelock.LockFile(self.asset_file, timeout=1)
        try:
            # Temporary unique name to use while downloading
            temp = '%s.%s' % (self.asset_file,
                              next(tempfile._get_candidate_names()))
            url_download(url, temp)
            # Acquire lock only after download the file
            lock.acquire()
            shutil.copy(temp, self.asset_file)
            time.sleep(60)
            self._compute_hash()
            return self._verify()
        finally:
            os.remove(temp)
            lock.release()

    def _compute_hash(self):
        result = crypto.hash_file(self.asset_file, algorithm=self.algorithm)
        basename = os.path.basename(self.asset_file)
        with open(self.hashfile, 'w') as f:
            f.write('%s %s\n' % (self.algorithm, result))

    def _get_hash_from_file(self):
        discovered = None
        if not os.path.isfile(self.hashfile):
            self._compute_hash()

        with open(self.hashfile, 'r') as f:
            for line in f.readlines():
                # md5 is 32 chars big and sha512 is 128 chars big.
                # others supported algorithms are between those.
                pattern = '%s [a-f0-9]{32,128}' % self.algorithm
                if re.match(pattern, line):
                    discovered = line.split()[1]
                    break
        return discovered

    def _verify(self):
        if not self.asset_hash:
            return True
        if self._get_hash_from_file() == self.asset_hash:
            return True
        else:
            return False

    def _get_local_file(self, path):
        lock = filelock.LockFile(self.asset_file)
        try:
            lock.acquire()
            os.symlink(path, self.asset_file)
            self._compute_hash()
            return self._verify()
        except OSError as e:
            if e.errno == errno.EEXIST:
                os.remove(self.asset_file)
                os.symlink(path, self.asset_file)
                self._compute_hash()
                return self._verify()
        finally:
            lock.release()

    @staticmethod
    def _is_expired(path, expire):
        if expire is None:
            return False
        creation_time = os.lstat(path)[stat.ST_CTIME]
        expire_time = creation_time + expire
        if time.time() > expire_time:
            return True
        return False
