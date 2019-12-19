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
import json
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


LOG = logging.getLogger('avocado.test')
#: The default hash algorithm to use on asset cache operations
DEFAULT_HASH_ALGORITHM = 'sha1'
#: The default location for assets download into the cache
LOCATION = 'by_location'


class UnsupportedProtocolError(EnvironmentError):
    """
    Signals that the protocol of the asset URL is not supported
    """


class Asset:
    """
    Handles assets from from multiple locations.
    """

    def __init__(self, name, asset_hash=None, algorithm=None, locations=None,
                 cache_dirs=None, expire=None, metadata=None):
        """
        Initialize the Asset() class.

        :param name: the asset filename. url is also supported
        :param asset_hash: asset hash
        :param algorithm: hash algorithm
        :param locations: location(s) where the asset can be fetched from
        :param cache_dirs: list of cache directories
        :param expire: time in seconds for the asset to expire
        :param metadata: metadata which will be saved inside metadata file
        """
        parsed_url = urlparse.urlparse(name)
        # Asset file name
        self.basename = os.path.basename(parsed_url.path)
        self.asset_hash = asset_hash

        if algorithm:
            self.algorithm = algorithm
        else:
            self.algorithm = DEFAULT_HASH_ALGORITHM

        self.locations = []
        # If `name` is an url, move it to `locations`
        if parsed_url.scheme:
            self.locations.append(os.path.dirname(parsed_url.geturl()))
        # Let's be conservative and check `locations` type
        if isinstance(locations, str):
            # remove asset name from location
            if self.basename in locations:
                parsed_locations = urlparse.urlparse(locations)
                self.locations.append(
                    os.path.dirname(parsed_locations.geturl()))
            else:
                self.locations.append(locations)
        elif isinstance(locations, list):
            # remove asset name from location
            for location in locations:
                if self.basename in location:
                    parsed_location = urlparse.urlparse(location)
                    self.locations.append(
                        os.path.dirname(parsed_location.geturl()))
                else:
                    self.locations.append(location)

        # Let's make the user's life easy and handle the cache
        if cache_dirs:
            self.cache_dirs = cache_dirs
        else:
            # Break early if we don't have the cache_dirs. This is necessary
            # so we don't change the Asset signature.
            raise EnvironmentError("At least one cache directory is necessary"
                                   " to download the asset.")

        self.expire = expire
        self.metadata = metadata

        # Break early. We need to know the source location of the asset.
        if not self.locations:
            raise EnvironmentError("An asset should have at least one source"
                                   " location. Double check your asset name"
                                   " and location and make sure to use a"
                                   " supported protocol.")

    def _create_hash_file(self, asset_path):
        """
        Compute the hash of the asset file and add it to the CHECKSUM
        file.

        :param asset_file: full path of the asset file.
        """
        result = crypto.hash_file(asset_path, algorithm=self.algorithm)
        with open(self._get_hash_file(asset_path), 'w') as hash_file:
            hash_file.write('%s %s\n' % (self.algorithm, result))

    def _create_metadata_file(self, asset_dir):
        """
        Creates JSON file with metadata.
        The file will be saved as `asset_file`_metadata.json

        :param asset_dir: full path where the asset file is located.
        """
        metadata_file_name = "%s_metadata.json" % self.basename
        metadata_path = os.path.join(os.path.dirname(asset_dir),
                                     metadata_file_name)
        metadata = json.dumps(self.metadata)
        with open(metadata_path, "w") as metadata_file:
            metadata_file.write(metadata)

    def _download(self, url_obj, asset_path):
        """
        Download the asset from an url.

        :param url_obj: object from urlparse.
        :param asset_path: full path of the asset file.
        :returns: if the downloaded file matches the hash.
        :rtype: bool
        """
        try:
            # Temporary unique name to use while downloading
            temp = '%s.%s' % (asset_path,
                              next(tempfile._get_candidate_names()))  # pylint: disable=W0212
            url_download(url_obj.geturl(), temp)

            # Acquire lock only after download the file
            with FileLock(asset_path, 1):
                shutil.move(temp, asset_path)
                self._create_hash_file(asset_path)
                return self._verify(asset_path)
        except OSError:
            if os.path.isfile(temp):
                os.remove(temp)
            elif os.path.isfile(asset_path):
                os.remove(asset_path)

    @staticmethod
    def _get_hash_file(asset_path):
        """
        Returns the file name that contains the hash for a given asset file

        :param asset_path: full path of the asset file.
        :returns: the CHECKSUM path
        :rtype: str
        """
        return '%s-CHECKSUM' % asset_path

    def _get_hash_from_file(self, asset_path):
        """
        Read the CHECKSUM file from the asset and return the hash.

        :param asset_path: full path of the asset file.
        :returns: the hash, if it exists.
        :rtype: str
        """
        discovered = None
        hash_file = self._get_hash_file(asset_path)
        if not os.path.isfile(hash_file):
            self._create_hash_file(asset_path)

        with open(hash_file, 'r') as hash_file:
            hash_value = hash_file.read()
            # md5 is 32 chars big and sha512 is 128 chars big.
            # others supported algorithms are between those.
            pattern = '%s [a-f0-9]{32,128}' % self.algorithm
            if re.match(pattern, hash_value):
                discovered = hash_value.split()[1]
        return discovered

    def _get_local_file(self, url_obj, asset_path):
        """
        Create a symlink for a local file into the cache.

        :param url_obj: object from urlparse.
        :param asset_path: full path of the asset file.
        :returns: if the local file matches the hash.
        :rtype: bool
        """
        with FileLock(asset_path, 1):
            try:
                os.symlink(url_obj.path, asset_path)
                self._create_hash_file(asset_path)
            except OSError as detail:
                if detail.errno == errno.EEXIST:
                    os.remove(asset_path)
                    os.symlink(url_obj.path, asset_path)
                    self._create_hash_file(asset_path)

        return self._verify(asset_path)

    @staticmethod
    def _get_relative_dir(url):
        """
        All assets are saved on `LOCATION/hash_from_location`. This way we
        know all assets are under `LOCATION`, making it easy to extend
        command-line functionalities like assets `list` or `search`.

        :param url: asset url/directory location.
        :returns: target location of asset the file.
        :rtype: str
        """
        url_hash = hashlib.new(DEFAULT_HASH_ALGORITHM,
                               url.encode(astring.ENCODING))
        return os.path.join(LOCATION, url_hash.hexdigest())

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
    def _is_expired(asset_path, expire):
        """
        Checks if a file is expired according to expired parameter.

        :param path: full path of the asset file.
        :returns: the expired status of an asset.
        :rtype: bool
        """
        if expire is None:
            return False
        creation_time = os.lstat(asset_path)[stat.ST_CTIME]
        expire_time = creation_time + expire
        if time.time() > expire_time:
            return True
        return False

    def _verify(self, asset_path):
        """
        Verify if the `asset_path` hash matches the hash in the hash file.

        :param asset_path: full path of the asset file.
        :returns: True when self.asset_hash is None or when it has the same
        value as the hash of the asset_file, otherwise return False.
        :rtype: bool
        """
        return bool(not self.asset_hash or
                    (self.asset_hash and
                     self._get_hash_from_file(asset_path) == self.asset_hash))

    def fetch(self):
        """
        Fetches the asset. First tries to find the asset on the provided
        cache_dirs list. Then tries to download the asset from the locations
        list provided.

        :raise EnvironmentError: When it fails to fetch the asset
        :returns: The path for the file on the cache directory.
        :rtype: str
        """
        # First let's search for the file in each one of the cache locations
        asset_path = self.find_asset_file()
        # If asset file exists locally, let's create the metadata and return
        # the path to the file.
        if asset_path:
            if self.metadata:
                self._create_metadata_file(asset_path)
            return asset_path

        # If we get to this point, we have to download the asset.
        # We need a writable cache directory. The first available writable
        # cache directory is used.
        cache_dir = self._get_writable_cache_dir()

        # We have a writable cache_dir. Let's get the asset.
        # Download asset from first available url and return its local path.
        for location in self.locations:
            url = os.path.join(location, self.basename)
            urlobj = urlparse.urlparse(url)
            # Select the correct transport protocol.
            if urlobj.scheme in ['http', 'https', 'ftp']:
                fetch_func = self._download
            elif urlobj.scheme == 'file':
                fetch_func = self._get_local_file
            else:
                raise UnsupportedProtocolError("Unsupported protocol"
                                               ": %s" % urlobj.scheme)

            # Create the target directory for the asset
            relative_dir = self._get_relative_dir(location)
            asset_path = os.path.join(cache_dir, relative_dir, self.basename)
            dirname = os.path.dirname(asset_path)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)

            # Let's try to download the asset.
            try:
                if fetch_func(urlobj, asset_path):
                    # Success! Create metadata.
                    if self.metadata:
                        self._create_metadata_file(asset_path)
                    return asset_path
                # If fetch_func returns False, we have a hash mismatch
                raise EnvironmentError("Hash mismatch for asset %s."
                                       % self.basename)
            except Exception:  # pylint: disable=W0703
                exc_type, exc_value = sys.exc_info()[:2]
                LOG.error('%s: %s', exc_type.__name__, exc_value)

        # If we get here, we could not download the asset.
        raise EnvironmentError("Failed to fetch %s." % self.basename)

    def find_asset_file(self):
        """
        Search for the asset file in each one of the cache locations

        :return: asset file if exists or None
        :rtype: str or None
        """
        for cache_dir in self.cache_dirs:
            cache_dir = os.path.expanduser(cache_dir)

            for location in self.locations:
                relative_dir = self._get_relative_dir(location)
                asset_path = os.path.join(cache_dir,
                                          relative_dir,
                                          self.basename)

                # To use a cached file, it must:
                # - Exists.
                # - Be valid (not expired).
                # - Be verified (hash check).
                if (os.path.isfile(asset_path) and
                        not self._is_expired(asset_path, self.expire)):
                    try:
                        with FileLock(asset_path, 30):
                            if self._verify(asset_path):
                                return asset_path
                    except Exception:  # pylint: disable=W0703
                        exc_type, exc_value = sys.exc_info()[:2]
                        LOG.error('%s: %s', exc_type.__name__, exc_value)
        return None

    def get_metadata(self):
        """
        Returns metadata of the asset if it exists or None.

        :return: metadata
        :rtype: dict or None
        """
        asset_path = self.find_asset_file()
        if asset_path:
            metadata_file_name = "%s_metadata.json" % self.basename
            metadata_path = os.path.join(os.path.dirname(asset_path),
                                         metadata_file_name)
            if os.path.isfile(metadata_path):
                with open(metadata_path, "r") as metadata_file:
                    metadata = json.loads(metadata_file.read())
                    return metadata
        return None
