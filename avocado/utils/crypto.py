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

import logging
import os
import random
import string
import shutil
try:
    import hashlib
except ImportError:
    import md5
    import sha

from avocado.utils import process


def get_random_string(length, ignore_str=string.punctuation,
                      convert_str=""):
    """
    Return a random string using alphanumeric characters.

    :param length: Length of the string that will be generated.
    :param ignore_str: Characters that will not include in generated string.
    :param convert_str: Characters that need to be escaped (prepend "\\").

    :return: The generated random string.
    """
    r = random.SystemRandom()
    result = ""
    chars = string.letters + string.digits + string.punctuation
    if not ignore_str:
        ignore_str = ""
    for i in ignore_str:
        chars = chars.replace(i, "")

    while length > 0:
        tmp = r.choice(chars)
        if convert_str and (tmp in convert_str):
            tmp = "\\%s" % tmp
        result += tmp
        length -= 1
    return result


def get_random_id():
    """
    Return a random string suitable for use as a qemu id.
    """
    return "id" + get_random_string(6)


def hash_wrapper(algorithm='md5', data=None):
    """
    Returns an hash object of data using md5 or sha1.

    This function is implemented in order to encapsulate hash objects in a
    way that is compatible with python 2.4 and python 2.6 without warnings.

    Note that even though python 2.6 hashlib supports hash types other than
    md5 and sha1, we are artificially limiting the input values in order to
    make the function to behave exactly the same among both python
    implementations.

    :param input: Optional input string that will be used to update the hash.
    :returns: Hash object.
    """
    if algorithm not in ['md5', 'sha1']:
        raise ValueError("Unsupported hash algorithm: %s" % algorithm)

    try:
        hash_obj = hashlib.new(algorithm)
    except NameError:
        if type == 'md5':
            hash_obj = md5.new()
        elif type == 'sha1':
            hash_obj = sha.new()

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


def create_x509_dir(path, cacert_subj, server_subj, passphrase,
                    secure=False, bits=1024, days=1095):
    """
    Creates directory with freshly generated:
    ca-cart.pem, ca-key.pem, server-cert.pem, server-key.pem,

    :param path: defines path to directory which will be created
    :param cacert_subj: ca-cert.pem subject
    :param server_key.csr: subject
    :param passphrase: passphrase to ca-key.pem
    :param secure: defines if the server-key.pem will use a passphrase
    :param bits: bit length of keys
    :param days: cert expiration

    :raise ValueError: openssl not found or rc != 0
    :raise OSError: if os.makedirs() fails
    """

    ssl_cmd = process.find_command("openssl")
    path = path + os.path.sep  # Add separator to the path
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path)

    server_key = "server-key.pem.secure"
    if secure:
        server_key = "server-key.pem"

    cmd_set = [
        ('%s genrsa -des3 -passout pass:%s -out %sca-key.pem %d' %
         (ssl_cmd, passphrase, path, bits)),
        ('%s req -new -x509 -days %d -key %sca-key.pem -passin pass:%s -out '
         '%sca-cert.pem -subj "%s"' %
         (ssl_cmd, days, path, passphrase, path, cacert_subj)),
        ('%s genrsa -out %s %d' % (ssl_cmd, path + server_key, bits)),
        ('%s req -new -key %s -out %s/server-key.csr -subj "%s"' %
         (ssl_cmd, path + server_key, path, server_subj)),
        ('%s x509 -req -passin pass:%s -days %d -in %sserver-key.csr -CA '
         '%sca-cert.pem -CAkey %sca-key.pem -set_serial 01 -out %sserver-cert.pem' %
         (ssl_cmd, passphrase, days, path, path, path, path))
    ]

    if not secure:
        cmd_set.append('%s rsa -in %s -out %sserver-key.pem' %
                       (ssl_cmd, path + server_key, path))

    for cmd in cmd_set:
        process.run(cmd)
        logging.info(cmd)
