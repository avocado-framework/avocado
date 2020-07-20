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

_RAND_POOL = random.SystemRandom()


def create_unique_job_id():
    """
    Create a 40 digit hex number to be used as a job ID string.
    (similar to SHA1)

    :return: 40 digit hex number string
    :rtype: str
    """
    return hashlib.sha1(hex(_RAND_POOL.getrandbits(160)).encode()).hexdigest()
