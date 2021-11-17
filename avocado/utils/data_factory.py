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

"""
Generate data useful for the avocado framework and tests themselves.
"""

import logging
import os
import random
import string
import tempfile

_RAND_POOL = random.SystemRandom()

log = logging.getLogger('avocado.test')


def generate_random_string(length, ignore=string.punctuation,
                           convert=""):
    """
    Generate a random string using alphanumeric characters.

    :param length: Length of the string that will be generated.
    :type length: int
    :param ignore: Characters that will not include in generated string.
    :type ignore: str
    :param convert: Characters that need to be escaped (prepend "\\").
    :type convert: str

    :return: The generated random string.
    """
    result = ""
    chars = string.ascii_letters + string.digits + string.punctuation
    if not ignore:
        ignore = ""
    for i in ignore:
        chars = chars.replace(i, "")

    while length > 0:
        tmp = _RAND_POOL.choice(chars)
        if convert and (tmp in convert):
            tmp = "\\%s" % tmp
        result += tmp
        length -= 1
    return result


def make_dir_and_populate(basedir='/tmp'):
    """
    Create a directory in basedir and populate with a number of files.

    The files just have random text contents.

    :param basedir: Base directory where directory should be generated.
    :type basedir: str
    :return: Path of the dir created and populated.
    :rtype: str
    """
    try:
        path = tempfile.mkdtemp(prefix='avocado_' + __name__,
                                dir=basedir)
        n_files = _RAND_POOL.randint(100, 150)
        for _ in range(n_files):
            fd, _ = tempfile.mkstemp(dir=path, text=True)
            str_length = _RAND_POOL.randint(30, 50)
            n_lines = _RAND_POOL.randint(5, 7)
            for _ in range(n_lines):
                os.write(fd, generate_random_string(str_length))
            os.close(fd)
    except OSError as details:
        log_msg = "Failed to generate dir in '%s' and populate: %s"
        log.error(log_msg, basedir, details)
        return None

    return path
