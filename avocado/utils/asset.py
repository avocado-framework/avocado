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
import urllib.parse

from . import astring, crypto
from . import path as utils_path
from .download import url_download
from .filelock import FileLock

LOG = logging.getLogger('avocado.test')
#: The default hash algorithm to use on asset cache operations
DEFAULT_HASH_ALGORITHM = 'sha1'


class UnsupportedProtocolError(OSError):
    """
    Signals that the protocol of the asset URL is not supported
    """


class Asset:
    """
    Try to fetch/verify an asset file from multiple locations.
    """

    def __init__(self, name, asset_hash, algorithm, locations, cache_dirs,
                 expire=None, metadata=None):
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
        self.name = name
        self.asset_hash = asset_hash

        self.parsed_name = urllib.parse.urlparse(self.name)

        # we currently support the following options for name and locations:
        # 1. name is a full URI and locations is empty;
        # 2. name is a single file name and locations is one or more entries.
        # raise an exception if we have an unsupported use of those arguments
        if ((self.parsed_name.scheme and locations is not None) or
                (not self.parsed_name.scheme and locations is None)):
            raise ValueError("Incorrect use of parameter name with parameter"
                             " locations.")

        if algorithm is None:
            self.algorithm = DEFAULT_HASH_ALGORITHM
        else:
            self.algorithm = algorithm

        if isinstance(locations, str):
            self.locations = [locations]
        else:
            self.locations = locations
        self.cache_dirs = cache_dirs
        self.expire = expire
        self.metadata = metadata

        # set asset_name according to parsed_name
        self.asset_name = os.path.basename(self.parsed_name.path)
        # set relative_dir for the asset
        self.relative_dir = os.path.join(self._get_relative_dir(),
                                         self.asset_name)

    def _create_hash_file(self, asset_path):
        """
        Compute the hash of the asset file and add it to the CHECKSUM
        file.

        :param asset_path: full path of the asset file.
        """
        result = crypto.hash_file(asset_path, algorithm=self.algorithm)
        with open(self._get_hash_file(asset_path), 'w') as hash_file:
            hash_file.write('%s %s\n' % (self.algorithm, result))

    def _create_metadata_file(self, asset_file):
        """
        Creates JSON file with metadata.
        The file will be saved as `asset_file`_metadata.json

        :param asset_file: The asset whose metadata will be saved
        :type asset_file: str
        """
        if self.metadata is not None:
            basename = os.path.splitext(asset_file)[0]
            metadata_path = "%s_metadata.json" % basename
            with open(metadata_path, "w") as metadata_file:
                json.dump(self.metadata, metadata_file)

    def _download(self, url_obj, asset_path):
        """
        Download the asset from an uri.

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
                shutil.copy(temp, asset_path)
                self._create_hash_file(asset_path)
                return self._verify_hash(asset_path)
        finally:
            try:
                os.remove(temp)
            except FileNotFoundError:
                LOG.info("Temporary asset file unavailable due to failed"
                         " download attempt.")

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
            for line in hash_file:
                # md5 is 32 chars big and sha512 is 128 chars big.
                # others supported algorithms are between those.
                pattern = '%s [a-f0-9]{32,128}' % self.algorithm
                if re.match(pattern, line):
                    discovered = line.split()[1]
                    break
        return discovered

    def _get_local_file(self, url_obj, asset_path):
        """
        Create a symlink for a local file into the cache.

        :param url_obj: object from urlparse.
        :param asset_path: full path of the asset file.
        :returns: if the local file matches the hash.
        :rtype: bool
        """
        if os.path.isdir(url_obj.path):
            path = os.path.join(url_obj.path, self.name)
        else:
            path = url_obj.path

        with FileLock(asset_path, 1):
            try:
                os.symlink(path, asset_path)
                self._create_hash_file(asset_path)
                return self._verify_hash(asset_path)
            except OSError as detail:
                if detail.errno == errno.EEXIST:
                    os.remove(asset_path)
                    os.symlink(path, asset_path)
                    self._create_hash_file(asset_path)
                    return self._verify_hash(asset_path)

    def _get_relative_dir(self):
        """
        When an asset name is not an URI, and:
          1. it also has a hash;
          2. or it has multiple locations;
        there's a clear intention for it to be unique *by name*, overwriting
        it if the file is corrupted or expired. These will be stored in the
        cache directory indexed by name.

        When an asset name is an URI, whether it has a hash or not, it will be
        saved according to their locations, so that multiple assets with the
        same file name, but completely unrelated to each other, will still
        coexist.

        :returns: target location of asset the file.
        :rtype: str
        """
        if (not self.parsed_name.scheme and
                (self.asset_hash or len(self.locations) > 1)):
            return 'by_name'

        # check if the URI is located on self.locations or self.parsed_name
        if self.locations is not None:
            # if it is on self.locations, we need to check if it has the
            # asset name on it or a trailing '/'
            if ((self.asset_name in self.locations[0]) or
                    (self.locations[0][-1] == '/')):
                base_url = os.path.dirname(self.locations[0])
            else:
                # here, self.locations is a pure conformant URI
                base_url = self.locations[0]
        else:
            # the URI is on self.parsed_name
            base_url = os.path.dirname(self.parsed_name.geturl())

        base_url_hash = hashlib.new(DEFAULT_HASH_ALGORITHM,
                                    base_url.encode(astring.ENCODING))

        return os.path.join('by_location', base_url_hash.hexdigest())

    def _get_writable_cache_dir(self):
        """
        Returns the first available writable cache directory

        When a asset has to be downloaded, a writable cache directory
        is then needed. The first available writable cache directory
        will be used.

        :returns: the first writable cache dir
        :rtype: str
        :raises: OSError
        """
        for cache_dir in self.cache_dirs:
            cache_dir = os.path.expanduser(cache_dir)
            if utils_path.usable_rw_dir(cache_dir):
                return cache_dir
        raise OSError("Can't find a writable cache directory.")

    @staticmethod
    def _is_expired(path, expire):
        """
        Checks if a file is expired according to expired parameter.

        :param path: full path of the asset file.
        :returns: the expired status of an asset.
        :rtype: bool
        """
        if expire is None:
            return False
        creation_time = os.lstat(path)[stat.ST_CTIME]
        expire_time = creation_time + expire
        if time.time() > expire_time:
            return True
        return False

    def _verify_hash(self, asset_path):
        """
        Verify if the `asset_path` hash matches the hash in the hash file.

        :param asset_path: full path of the asset file.
        :returns: True when self.asset_hash is None or when it has the same
        value as the hash of the asset_file, otherwise return False.
        :rtype: bool
        """
        if self.asset_hash is None or (
                self._get_hash_from_file(asset_path) == self.asset_hash):
            return True
        return False

    def fetch(self):
        """
        Fetches the asset. First tries to find the asset on the provided
        cache_dirs list. Then tries to download the asset from the locations
        list provided.

        :raise OSError: When it fails to fetch the asset
        :returns: The path for the file on the cache directory.
        :rtype: str
        """
        urls = []
        # If name is actually an url, it has to be included in urls list
        if self.parsed_name.scheme:
            urls.append(self.parsed_name.geturl())

        # First let's search for the file in each one of the cache locations
        asset_file = None
        try:
            asset_file = self.find_asset_file()
        except OSError:
            LOG.info("Asset not in cache, fetching it.")

        if asset_file is not None:
            if self.metadata is not None:
                self._create_metadata_file(asset_file)
            return asset_file

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
            urlobj = urllib.parse.urlparse(url)
            if urlobj.scheme in ['http', 'https', 'ftp']:
                fetch = self._download
            elif urlobj.scheme == 'file':
                fetch = self._get_local_file
            else:
                raise UnsupportedProtocolError("Unsupported protocol"
                                               ": %s" % urlobj.scheme)
            asset_file = os.path.join(cache_dir,
                                      self.relative_dir)
            dirname = os.path.dirname(asset_file)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            try:
                if fetch(urlobj, asset_file):
                    if self.metadata is not None:
                        self._create_metadata_file(asset_file)
                    return asset_file
            except Exception:  # pylint: disable=W0703
                exc_type, exc_value = sys.exc_info()[:2]
                LOG.error('%s: %s', exc_type.__name__, exc_value)

        raise OSError("Failed to fetch %s." % self.asset_name)

    def find_asset_file(self):
        """
        Search for the asset file in each one of the cache locations

        :return: asset path, if it exists in the cache
        :rtype: str
        :raises: OSError
        """

        for cache_dir in self.cache_dirs:
            cache_dir = os.path.expanduser(cache_dir)
            asset_file = os.path.join(cache_dir, self.relative_dir)

            # To use a cached file, it must:
            # - Exists.
            # - Be valid (not expired).
            # - Be verified (hash check).
            if (os.path.isfile(asset_file) and
                    not self._is_expired(asset_file, self.expire)):
                try:
                    with FileLock(asset_file, 30):
                        if self._verify_hash(asset_file):
                            return asset_file
                except Exception:  # pylint: disable=W0703
                    exc_type, exc_value = sys.exc_info()[:2]
                    LOG.error('%s: %s', exc_type.__name__, exc_value)

        raise OSError("File %s not found in the cache." % self.asset_name)

    def get_metadata(self):
        """
        Returns metadata of the asset if it exists or None.

        :return: metadata
        :rtype: dict or None
        """
        try:
            asset_file = self.find_asset_file()
        except OSError:
            raise OSError("Metadata not available.")

        basename = os.path.splitext(asset_file)[0]
        metadata_file = "%s_metadata.json" % basename
        if os.path.isfile(metadata_file):
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
                return metadata
