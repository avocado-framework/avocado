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
URL related functions.

The strange name is to avoid accidental naming collisions in code.
"""

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse


def is_url(path):
    """
    Return `True` if path looks like an URL.

    :param path: path to check.
    :rtype: Boolean.
    """
    url_parts = urlparse.urlparse(path)
    return (url_parts[0] in ('http', 'https', 'ftp', 'git'))
