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
import stat
import sys
import time
import urlparse

from . import crypto
from . import path as utils_path
from .download import url_download


log = logging.getLogger('avocado.test')


class LockException(Exception):
    pass


class LockFile(object):
    def __init__(self, lockfile, timeout):
        # Timeout defaults to 1 second
        if timeout is None:
            timeout = 1

        self.lockfile = '%s.lock' % lockfile
        self.timeout = time.time() + timeout

    def acquire(self):
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        while time.time() < self.timeout:
            try:
                os.open(self.lockfile, flags)
                return
            except:
                time.sleep(0.1)
        raise LockException('Cannot acquire lock (%s exists)' % self.lockfile)

    def release(self):
        try:
            os.remove(self.lockfile)
        except:
            pass


class Asset(object):
    """
    Try to fetch/verify an asset file from multiple locations.
    """

    def __init__(self, name, asset_hash, algorithm, locations, cache_dirs,
                 expire, lock_timeout):
        """
        Initialize the Asset() and fetches the asset file. The path for
        the fetched file can be reached using the self.path attribute.

        :param name: the asset filename. url is also supported
        :param asset_hash: asset hash
        :param algorithm: hash algorithm
        :param locations: list of locations fetch asset from
        :params cache_dirs: list of cache directories
        :params expire: time in seconds for the asset to expire
        """
        self.name = name
        self.asset_hash = asset_hash
        self.algorithm = algorithm
        self.locations = locations
        self.cache_dirs = cache_dirs
        self.nameobj = urlparse.urlparse(self.name)
        self.basename = os.path.basename(self.nameobj.path)
        self.expire = expire
        self.lock_timeout = lock_timeout

    def fetch(self):
        urls = []

        # If name is actually an url, it has to be included in urls list
        if self.nameobj.scheme:
            urls.append(self.nameobj.geturl())

        # First let's find for the file in all cache locations
        for cache_dir in self.cache_dirs:
            cache_dir = os.path.expanduser(cache_dir)
            self.asset_file = os.path.join(cache_dir, self.basename)

            # To use a cached file, it must:
            # - Exists.
            # - Be valid (not expired).
            # - Be verified (hash check).
            if (os.path.isfile(self.asset_file) and
               not self._is_expired(self.asset_file, self.expire) and
               self._verify(self.asset_file, self.asset_hash, self.algorithm)):
                return self.asset_file

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
                        self._download(url, self.asset_file, self.lock_timeout)
                        if self._verify(self.asset_file, self.asset_hash,
                                        self.algorithm):
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
                        self._get_local_file(path, self.asset_file,
                                             self.lock_timeout)
                        if self._verify(self.asset_file, self.asset_hash,
                                        self.algorithm):
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

    @staticmethod
    def _is_expired(path, expire):
        if expire is None:
            return False
        creation_time = os.lstat(path)[stat.ST_CTIME]
        expire_time = creation_time + expire
        if time.time() > expire_time:
            return True
        return False

    @staticmethod
    def _download(url, dst, lock_timeout):
        lock = LockFile(dst, timeout=lock_timeout)
        lock.acquire()
        try:
            url_download(url, dst)
        finally:
            lock.release()

    @staticmethod
    def _get_local_file(path, dst, lock_timeout):
        lock = LockFile(dst, timeout=lock_timeout)
        lock.acquire()
        try:
            os.symlink(path, dst)
        except OSError as e:
            if e.errno == errno.EEXIST:
                os.remove(dst)
                os.symlink(path, dst)
        finally:
            lock.release()

    @staticmethod
    def _verify(path, expected_hash, algorithm):
        if not os.path.isfile(path):
            return False

        if not expected_hash:
            return True

        hashresult = crypto.hash_file(path, algorithm=algorithm)
        if hashresult == expected_hash:
            return True
        else:
            log.error('Asset file seems corrupted. '
                      'Expected hash: %s, actual hash: %s.'
                      % (expected_hash, hashresult))
            return False
