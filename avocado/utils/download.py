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
# This code was inspired in the autotest project,
# client/shared/utils.py
# Authors: Martin J Bligh <mbligh@google.com>, Andy Whitcroft <apw@shadowen.org>


"""
Methods to download URLs and regular files.
"""

import logging
import os
import socket
import shutil
import urllib2

from avocado.utils import aurl


log = logging.getLogger('avocado.test')


def url_open(url, data=None, timeout=5):
    """
    Wrapper to :func:`urllib2.urlopen` with timeout addition.

    :param url: URL to open.
    :param data: (optional) data to post.
    :param timeout: (optional) default timeout in seconds.
    :return: file-like object.
    :raises: `URLError`.
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

    :param url: source URL.
    :param filename: destination path.
    :param data: (optional) data to post.
    :param timeout: (optional) default timeout in seconds.
    :return: `None`.
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

    :param src: source path or URL. May be local or a remote file.
    :param dst: destination path.
    :param permissions: (optional) set access permissions.
    :return: destination path.
    """
    if src == dst:
        return

    if aurl.is_url(src):
        url_download(src, dst)
    else:
        shutil.copyfile(src, dst)

    if permissions:
        os.chmod(dst, permissions)
    return dst
