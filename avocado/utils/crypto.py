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
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""Cryptographic hash utilities for file verification."""

import hashlib
import io
import logging
import os

LOG = logging.getLogger(__name__)


def hash_file(filename, size=None, algorithm="md5"):
    """Calculate the hash value of a file.

    Computes a cryptographic hash of the specified file using the given
    algorithm. Optionally limits hashing to the first N bytes of the file,
    which is useful for verifying partial downloads or large files.

    :param filename: Path of the file that will have its hash calculated.
    :type filename: str
    :param size: If provided, hash only the first size bytes of the file.
        If None or 0, the entire file is hashed. If size exceeds the file
        size, the entire file is hashed.
    :type size: int or None
    :param algorithm: Hash algorithm to use. Supported algorithms include
        md5, sha1, sha256, sha512, blake2b, and others available in hashlib.
    :type algorithm: str
    :return: Hexadecimal digest string of the computed hash. Returns None
        if an invalid algorithm is specified.
    :rtype: str or None
    :raises FileNotFoundError: When the specified file does not exist.
    :raises PermissionError: When the file cannot be read due to permissions.

    Example::

        >>> hash_file('/path/to/file')
        'abc123...'
        >>> hash_file('/path/to/file', algorithm='sha256')
        'e3b0c44298fc1c149afbf4c8996fb924...'
        >>> hash_file('/path/to/large_file', size=1024)
        'abc123...'
    """
    chunksize = io.DEFAULT_BUFFER_SIZE
    fsize = os.path.getsize(filename)

    if not size or size > fsize:
        size = fsize

    try:
        hash_obj = hashlib.new(algorithm)
    except ValueError as detail:
        LOG.error(
            'Returning "None" due to inability to create hash object: "%s"', detail
        )
        return None

    with open(filename, "rb") as file_to_hash:
        while size > 0:
            chunksize = min(chunksize, size)
            data = file_to_hash.read(chunksize)
            if not data:
                LOG.debug("Nothing left to read but size=%d", size)
                break
            hash_obj.update(data)
            size -= len(data)

    return hash_obj.hexdigest()


# pylint: disable=wrong-import-position
from avocado.utils.deprecation import log_deprecation

log_deprecation.warning("crypto")
