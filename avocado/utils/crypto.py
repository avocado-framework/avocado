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

import os
import logging
import hashlib


def hash_wrapper(algorithm='md5', data=None):
    """
    Returns an hash object of data using either md5 or sha1 only.

    :param input: Optional input string that will be used to update the hash.
    :returns: Hash object.
    """
    if algorithm not in ['md5', 'sha1']:
        raise ValueError("Unsupported hash algorithm: %s" % algorithm)

    hash_obj = hashlib.new(algorithm)
    if data:
        hash_obj.update(data)

    return hash_obj


def hash_file(filename, size=None, algorithm="md5"):
    """
    Calculate the hash value of filename.

    If size is not None, limit to first size bytes.
    Throw exception if something is wrong with filename.
    Can be also implemented with bash one-liner (assuming ``size%1024==0``)::

        dd if=filename bs=1024 count=size/1024 | sha1sum -

    :param filename: Path of the file that will have its hash calculated.
    :param method: Method used to calculate the hash. Supported methods:
                   * md5
                   * sha1
    :param size: If provided, hash only the first size bytes of the file.
    :return: Hash of the file, if something goes wrong, return None.
    """
    chunksize = 4096
    fsize = os.path.getsize(filename)

    if not size or size > fsize:
        size = fsize
    f = open(filename, 'rb')

    try:
        hash_obj = hash_wrapper(algorithm=algorithm)
    except ValueError:
        logging.error("Unknown hash algorithm %s, returning None", algorithm)

    while size > 0:
        if chunksize > size:
            chunksize = size
        data = f.read(chunksize)
        if len(data) == 0:
            logging.debug("Nothing left to read but size=%d", size)
            break
        hash_obj.update(data)
        size -= len(data)
    f.close()
    return hash_obj.hexdigest()
