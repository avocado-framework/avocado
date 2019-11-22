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
# Copyright: Red Hat Inc. 2019
# Authors: Lucas Meneghel Rodrigues <lmr@redhat.com>
#          Ruda Moura <rmoura@redhat.com>

"""
Test loader module.
"""

import os


def reference_split(reference):
    '''
    Splits a test reference into a path and additional info

    This should be used dependent on the specific type of resolver.  If
    a resolver is not expected to support multiple test references inside
    a given file, then this is not suitable.

    :returns: (path, additional_info)
    :type: (str, str or None)
    '''
    if not os.path.exists(reference):
        if ':' in reference:
            return reference.rsplit(':', 1)
    return (reference, None)
