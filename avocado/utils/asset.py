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
import operator
import os
import re
import shutil
import stat
import sys
import time
import uuid
from datetime import datetime
from urllib.parse import urlparse

from avocado.utils import astring, crypto
from avocado.utils import path as utils_path
from avocado.utils.download import url_download
from avocado.utils.filelock import FileLock

LOG = logging.getLogger(__name__)
#: The default hash algorithm to use on asset cache operations
DEFAULT_HASH_ALGORITHM = 'sha1'

#: The default timeout for the downloading of assets
DOWNLOAD_TIMEOUT = 300

SUPPORTED_OPERATORS = {'==': operator.eq,
                       '<': operator.lt,
                       '>': operator.gt,
                       '<=': operator.le,
                       '>=': operator.ge}


class UnsupportedProtocolError(OSError):
    """
    Signals that the protocol of the asset URL is not supported
    """


class Asset:
    """
    Try to fetch/verify an asset file from multiple locations.
    """

    def __init__(self, name=None, asset_hash=None, algorithm=None,
                 locations=None, cache_dirs=None, expire=None, metadata=None):
        """Initialize the Asset() class.

        :param name: the asset filename. url is also supported. Default is ''.
        :param asset_hash: asset hash
        :param algorithm: hash algorithm
        :param locations: location(s) where the asset can be fetched from
        :param cache_dirs: list of cache directories
        :param expire: time in seconds for the asset to expire
        :param metadata: metadata which will be saved inside metadata file
        """
        self.name = name or ''
        self.asset_hash = asset_hash

        if isinstance(locations, str):
            self.locations = [locations]
        else:
            self.locations = locations or []

        if algorithm is None:
            self.algorithm = DEFAULT_HASH_ALGORITHM
        else:
            self.algorithm = algorithm

        self.cache_dirs = cache_dirs or []
        self.expire = expire
        self.metadata = metadata

    def _create_hash_file(self, asset_path):
        """
        Compute the hash of the asset file and add it to the CHECKSUM
        file.

        :param asset_path: full path of the asset file.
        """
        result = crypto.hash_file(asset_path, algorithm=self.algorithm)
        hash_file = self._get_hash_file(asset_path)
        with FileLock(hash_file, 30):
            with open(hash_file, 'w') as fp:
                fp.write('%s %s\n' % (self.algorithm, result))

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

    def _download(self, url_obj, asset_path, timeout=None):
        """
        Download the asset from an uri.

        :param url_obj: object from urlparse.
        :param asset_path: full path of the asset file.
        :param timeout: timeout in seconds. Default is
                        :data:`avocado.utils.asset.DOWNLOAD_TIMEOUT`.
        :returns: if the downloaded file matches the hash.
        :rtype: bool
        """
        timeout = timeout or DOWNLOAD_TIMEOUT
        try:
            # Temporary unique name to use while downloading
            temp = '%s.%s' % (asset_path, str(uuid.uuid4()))

            # To avoid parallel downloads of the same asset, and errors during
            # the write after download, let's get the lock before start the
            # download.
            with FileLock(asset_path, 120):
                try:
                    self.find_asset_file(create_metadata=True)
                    return True
                except OSError:
                    LOG.debug("Asset not in cache after lock, fetching it.")

                url_download(url_obj.geturl(), temp, timeout=timeout)
                shutil.copy(temp, asset_path)
                self._create_hash_file(asset_path)
                if not self._verify_hash(asset_path):
                    msg = "Hash mismatch. Ignoring asset from the cache"
                    raise OSError(msg)
                return True
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
        hash_file = self._get_hash_file(asset_path)
        if not os.path.isfile(hash_file):
            self._create_hash_file(asset_path)

        return Asset.read_hash_from_file(hash_file)[1]

    @classmethod
    def read_hash_from_file(cls, filename):
        """Read the CHECKSUM file and return the hash.

        This method raises a FileNotFoundError if file is missing and assumes
        that filename is the CHECKSUM filename.

        :rtype: list with algorithm and hash
        """
        try:
            with FileLock(filename, 30):
                with open(filename, 'r') as hash_file:
                    for line in hash_file:
                        # md5 is 32 chars big and sha512 is 128 chars big.
                        # others supported algorithms are between those.
                        if re.match('^.* [a-f0-9]{32,128}', line):
                            return line.split()
        except Exception:  # pylint: disable=W0703
            exc_type, exc_value = sys.exc_info()[:2]
            LOG.error('%s: %s', exc_type.__name__, exc_value)
            return [None, None]

    def _get_local_file(self, url_obj, asset_path, _):
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
        if (not self.name_scheme and
                (self.asset_hash or len(self.locations) > 1)):
            return 'by_name'

        # check if the URI is located on self.locations or self.parsed_name
        if self.locations:
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
            if self.parsed_name.query:
                base_url = "%s://%s%s" % (self.parsed_name.scheme,
                                          self.parsed_name.netloc,
                                          self.parsed_name.path)
            else:
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
        if time.monotonic() > expire_time:
            return True
        return False

    @classmethod
    def _has_valid_hash(cls, asset_path, asset_hash=None):
        """Checks if a file has a valid hash based on the hash parameter.

        If asset_hash is None then will consider a valid asset.
        """
        if asset_hash is None:
            LOG.debug("No hash provided. Cannot check the asset file"
                      " integrity.")
            return True

        hash_path = cls._get_hash_file(asset_path)
        _, hash_from_file = cls.read_hash_from_file(hash_path)
        if hash_from_file == asset_hash:
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
        return self._has_valid_hash(asset_path, self.asset_hash)

    def fetch(self, timeout=None):
        """Try to fetch the current asset.

        First tries to find the asset on the provided cache_dirs list.
        Then tries to download the asset from the locations list
        provided.

        :param timeout: timeout in seconds. Default is
                        :data:`avocado.utils.asset.DOWNLOAD_TIMEOUT`.
        :raise OSError: When it fails to fetch the asset
        :returns: The path for the file on the cache directory.
        :rtype: str
        """
        # First let's search for the file in each one of the cache locations
        asset_file = None
        error = "Can't fetch: 'urls' is not defined."
        timeout = timeout or DOWNLOAD_TIMEOUT

        LOG.info("Fetching asset %s", self.name)
        try:
            return self.find_asset_file(create_metadata=True)
        except OSError:
            LOG.info("Asset not in cache, fetching it.")

        # If we get to this point, we have to download it from a location.
        # A writable cache directory is then needed. The first available
        # writable cache directory will be used.
        cache_dir = self._get_writable_cache_dir()
        # Now we have a writable cache_dir. Let's get the asset.
        for url in self.urls:
            if url is None:
                continue
            urlobj = urlparse(url)
            if urlobj.scheme in ['http', 'https', 'ftp']:
                fetch = self._download
            elif urlobj.scheme == 'file':
                fetch = self._get_local_file
            # We are assuming that everything starting with './' or '/' are a
            # file too.
            elif url.startswith(('/', './')):
                fetch = self._get_local_file
            else:
                raise UnsupportedProtocolError("Unsupported protocol"
                                               ": %s" % urlobj.scheme)
            asset_file = os.path.join(cache_dir,
                                      self.relative_dir)
            dirname = os.path.dirname(asset_file)
            if not os.path.isdir(dirname):
                os.makedirs(dirname, exist_ok=True)
            try:
                if fetch(urlobj, asset_file, timeout):
                    LOG.info("Asset downloaded.")
                    if self.metadata is not None:
                        self._create_metadata_file(asset_file)
                    return asset_file
            except Exception:  # pylint: disable=W0703
                exc_type, exc_value = sys.exc_info()[:2]
                LOG.error('%s: %s', exc_type.__name__, exc_value)
                error = exc_value

        raise OSError("Failed to fetch %s (%s)." % (self.asset_name, error))

    def find_asset_file(self, create_metadata=False):
        """
        Search for the asset file in each one of the cache locations

        :param bool create_metadata: Should this method create the
                                     metadata in case asset file found
                                     and metadata is not found?  Default
                                     is False.
        :return: asset path, if it exists in the cache
        :rtype: str
        :raises: OSError
        """

        for cache_dir in self.cache_dirs:
            cache_dir = os.path.expanduser(cache_dir)
            asset_file = os.path.join(cache_dir, self.relative_dir)

            # Ignore non-files
            if not os.path.isfile(asset_file):
                continue

            # Ignore expired asset files
            if self._is_expired(asset_file, self.expire):
                continue

            # Ignore mismatch hash
            if not self._has_valid_hash(asset_file, self.asset_hash):
                continue

            if create_metadata:
                self._create_metadata_file(asset_file)

            LOG.info("Asset already exists in cache.")
            return asset_file

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

    @property
    def asset_name(self):
        if self.parsed_name.query:
            return self.parsed_name.query
        return os.path.basename(self.parsed_name.path)

    @classmethod
    def get_all_assets(cls, cache_dirs, sort=True):
        """Returns all assets stored in all cache dirs."""
        assets = []
        for cache_dir in cache_dirs:
            expanded = os.path.expanduser(cache_dir)
            for root, _, files in os.walk(expanded):
                for f in files:
                    if not f.endswith('-CHECKSUM') and \
                       not f.endswith('_metadata.json'):
                        assets.append(os.path.join(root, f))
        if sort:
            assets = {a: os.stat(a).st_atime for a in assets}
            return [a[0] for a in sorted(assets.items(),
                                         key=lambda x: x[1],
                                         reverse=True)]
        return assets

    @classmethod
    def get_asset_by_name(cls, name, cache_dirs, expire=None, asset_hash=None):
        """This method will return a cached asset based on name if exists.

        You don't have to instantiate an object of Asset class. Just use this
        method.

        To be improved soon: cache_dirs should be not necessary.

        :param name: the asset filename used during registration.
        :param cache_dirs: list of directories to use during the search.
        :param expire: time in seconds for the asset to expire. Expired assets
                       will not be returned.
        :param asset_hash: asset hash.

        :return: asset path, if it exists in the cache.
        :rtype: str
        :raises: OSError
        """

        for cache_dir in cache_dirs:
            asset_file = os.path.join(os.path.expanduser(cache_dir),
                                      'by_name',
                                      name)

            # Ignore non-files
            if not os.path.isfile(asset_file):
                continue

            # Ignore expired asset files
            if cls._is_expired(asset_file, expire):
                continue

            # Ignore mismatch hash
            if not cls._has_valid_hash(asset_file, asset_hash):
                continue

            return asset_file

        raise OSError("File %s not found in the cache." % name)

    @classmethod
    def get_assets_unused_for_days(cls, days, cache_dirs):
        """Return a list of all assets in cache based on the access time.

        This will check if the file's data wasn't modified N days ago.

        :param days: how many days ago will be the threshold. Ex: "10" will
                     return the assets files that *was not* accessed during
                     the last 10 days.
        :param cache_dirs: list of directories to use during the search.
        """
        result = []
        for file_path in cls.get_all_assets(cache_dirs):
            stats = os.stat(file_path)
            diff = datetime.now() - datetime.fromtimestamp(stats.st_atime)
            if diff.days >= days:
                result.append(file_path)
        return result

    @classmethod
    def get_assets_by_size(cls, size_filter, cache_dirs):
        """Return a list of all assets in cache based on its size in MB.

        :param size_filter: a string with a filter (comparison operator +
                            value). Ex ">20", "<=200". Supported operators:
                            ==, <, >, <=, >=.
        :param cache_dirs: list of directories to use during the search.
        """
        try:
            op = re.match('^(\\D+)(\\d+)$', size_filter).group(1)
            value = int(re.match('^(\\D+)(\\d+)$', size_filter).group(2))
        except (AttributeError, ValueError):
            msg = ("Invalid syntax. You need to pass an comparison operatator",
                   " and a value. Ex: '>=200'")
            raise OSError(msg)

        try:
            method = SUPPORTED_OPERATORS[op]
        except KeyError:
            msg = ("Operator not supported. Currented valid values are: ",
                   ", ".join(SUPPORTED_OPERATORS))
            raise OSError(msg)

        result = []
        for file_path in cls.get_all_assets(cache_dirs):
            file_size = os.path.getsize(file_path)
            if method(file_size, value):
                result.append(file_path)
        return result

    @classmethod
    def remove_assets_by_overall_limit(cls, limit, cache_dirs):
        """This will remove assets based on overall limit.

        We are going to sort the assets based on the access time first.
        For instance it may be the case that a GitLab cache limit is 4
        GiB, in that case we can sort by last access, and remove all
        that exceeds 4 GiB (that is, keep the last accessed 4 GiB worth
        of cached files).

        Note: during the usage of this method, you should use bytes as limit.

        :param limit: a integer limit in bytes.
        :param cache_dirs: list of directories to use during the search.
        """
        size_sum = 0
        for asset in cls.get_all_assets(cache_dirs):
            size_sum += os.stat(asset).st_size
            if size_sum >= limit:
                cls.remove_asset_by_path(asset)

    @classmethod
    def remove_assets_by_size(cls, size_filter, cache_dirs):
        for file_path in cls.get_assets_by_size(size_filter, cache_dirs):
            cls.remove_asset_by_path(file_path)

    @classmethod
    def remove_assets_by_unused_for_days(cls, days, cache_dirs):
        for file_path in cls.get_assets_unused_for_days(days, cache_dirs):
            cls.remove_asset_by_path(file_path)

    @property
    def name_scheme(self):
        """This property will return the scheme part of the name if is an URL.

        Otherwise, will return None.
        """
        parsed = self.parsed_name
        if parsed:
            return parsed.scheme

    @property
    def name_url(self):
        """This property will return the full url of the name if is an URL.

        Otherwise, will return None.
        """
        if self.name_scheme:
            return self.parsed_name.geturl()

    @staticmethod
    def parse_name(name):
        """Returns a ParseResult object for the given name."""
        return urlparse(name)

    @property
    def parsed_name(self):
        """Returns a ParseResult object for the currently set name."""
        return self.parse_name(self.name)

    @property
    def relative_dir(self):
        return os.path.join(self._get_relative_dir(), self.asset_name)

    @classmethod
    def remove_asset_by_path(cls, asset_path):
        """Remove an asset and its checksum.

        To be fixed: Due the current implementation limitation, this method
        will not remove the metadata to avoid removing other asset metadata.

        :param asset_path: full path of the asset file.
        """
        os.remove(asset_path)
        filename = "{}-CHECKSUM".format(asset_path)
        os.remove(filename)

    @property
    def urls(self):
        """Complete list of locations including name if is an URL."""
        urls = []
        if self.name_scheme:
            urls.append(self.name_url)

        if self.locations:
            urls.extend(self.locations)

        return urls
