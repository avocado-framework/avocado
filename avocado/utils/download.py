# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: RedHat 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Methods to download URLs and regular files.
"""

import logging
import os
import socket
import shutil
import urllib2
import urlparse

log = logging.getLogger('avocado.test')


def is_url(path):
    """
    Return true if path looks like a URL
    """
    url_parts = urlparse.urlparse(path)
    return (url_parts[0] in ('http', 'https', 'ftp', 'git'))


def url_open(url, data=None, timeout=5):
    """
    Wrapper to urllib2.urlopen with timeout addition.
    """
    # Save old timeout
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        return urllib2.urlopen(url, data=data)
    finally:
        socket.setdefaulttimeout(old_timeout)


def url_download(url, filename, data=None, timeout=300):
    """
    Retrieve a file from given url.
    """
    log.info('Fetching %s -> %s', url, filename)

    src_file = url_open(url, data=data, timeout=timeout)
    try:
        dest_file = open(filename, 'wb')
        try:
            shutil.copyfileobj(src_file, dest_file)
        finally:
            dest_file.close()
    finally:
        src_file.close()


def get_file(src, dst, permissions=None):
    """
    Get a file from src and put it in dest, returning dest path.

    :param src: Source path or URL. May be local or a remote file.
    :param dst: Destination path.
    :returns: Destination path.
    """
    if src == dst:
        return

    if is_url(src):
        url_download(src, dst)
    else:
        shutil.copyfile(src, dst)

    if permissions:
        os.chmod(dst, permissions)
    return dst
