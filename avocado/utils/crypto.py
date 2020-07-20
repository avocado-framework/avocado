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

import hashlib
import io
import logging
import os


def hash_file(filename, size=None, algorithm="md5"):
    """
    Calculate the hash value of filename.

    If size is not None, limit to first size bytes.
    Throw exception if something is wrong with filename.
    Can be also implemented with bash one-liner (assuming ``size%1024==0``)::

        dd if=filename bs=1024 count=size/1024 | sha1sum -

    :param filename: Path of the file that will have its hash calculated.
    :param algorithm: Method used to calculate the hash (default is md5).
    :param size: If provided, hash only the first size bytes of the file.
    :return: Hash of the file, if something goes wrong, return None.
    """
    chunksize = io.DEFAULT_BUFFER_SIZE
    fsize = os.path.getsize(filename)

    if not size or size > fsize:
        size = fsize

    try:
        hash_obj = hashlib.new(algorithm)
    except ValueError as detail:
        logging.error('Returning "None" due to inability to create hash '
                      'object: "%s"', detail)
        return None

    with open(filename, 'rb') as file_to_hash:
        while size > 0:
            if chunksize > size:
                chunksize = size
            data = file_to_hash.read(chunksize)
            if len(data) == 0:
                logging.debug("Nothing left to read but size=%d", size)
                break
            hash_obj.update(data)
            size -= len(data)

    return hash_obj.hexdigest()
