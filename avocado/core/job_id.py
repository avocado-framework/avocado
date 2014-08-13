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
# Authors: Lucas Meneghel Rodrigues <lmr@redhat.com>

import hashlib
import random
import socket
import time

_RAND_POOL = random.SystemRandom()
_HOSTNAME = socket.gethostname()


def get_job_id():
    """
    Create a job ID SHA1.

    :return: SHA1 string
    :rtype: str
    """
    info = '%s-%s-%s' % (_HOSTNAME,
                         time.strftime('%Y-%m-%dT%H:%M:%S'),
                         _RAND_POOL.getrandbits(64))
    h = hashlib.sha1()
    h.update(info)
    return h.hexdigest()
