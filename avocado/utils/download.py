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

try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen

from . import aurl
from . import output
from . import crypto

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
        return urlopen(url, data=data)
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


def url_download_interactive(url, output_file, title='', chunk_size=102400):
    """
    Interactively downloads a given file url to a given output file.

    :type url: string
    :param url: URL for the file to be download
    :type output_file: string
    :param output_file: file name or absolute path on which to save the file to
    :type title: string
    :param title: optional title to go along the progress bar
    :type chunk_size: integer
    :param chunk_size: amount of data to read at a time
    """
    output_dir = os.path.dirname(output_file)
    output_file = open(output_file, 'w+b')
    input_file = urlopen(url)

    try:
        file_size = int(input_file.headers['Content-Length'])
    except KeyError:
        raise ValueError('Could not find file size in HTTP headers')

    logging.info('Downloading %s, %s to %s', os.path.basename(url),
                 output.display_data_size(file_size), output_dir)

    progress_bar = output.ProgressBar(maximum=file_size, title=title)

    # Download the file, while interactively updating the progress
    progress_bar.draw()
    while True:
        data = input_file.read(chunk_size)
        if data:
            progress_bar.append_amount(len(data))
            output_file.write(data)
        else:
            progress_bar.update_amount(file_size)
            break

    output_file.close()


def _get_file(src, dst, permissions=None):
    if src == dst:
        return

    if aurl.is_url(src):
        url_download(src, dst)
    else:
        shutil.copyfile(src, dst)

    if permissions:
        os.chmod(dst, permissions)
    return dst


def get_file(src, dst, permissions=None, hash_expected=None,
             hash_algorithm="md5", download_retries=1):
    """
    Gets a file from a source location, optionally using caching.

    If no hash_expected is provided, simply download the file. Else,
    keep trying to download the file until download_failures exceeds
    download_retries or the hashes match.

    If the hashes match, return dst. If download_failures exceeds
    download_retries, raise an EnvironmentError.

    :param src: source path or URL. May be local or a remote file.
    :param dst: destination path.
    :param permissions: (optional) set access permissions.
    :param hash_expected: Hash string that we expect the file downloaded to
            have.
    :param hash_algorithm: Algorithm used to calculate the hash string
            (md5, sha1).
    :param download_retries: Number of times we are going to retry a failed
            download.
    :raise: EnvironmentError.
    :return: destination path.
    """
    def _verify_hash(filename):
        if os.path.isfile(filename):
            return crypto.hash_file(filename, algorithm=hash_algorithm)
        return None

    if hash_expected is None:
        return _get_file(src, dst, permissions)

    download_failures = 0
    hash_file = _verify_hash(dst)

    while not hash_file == hash_expected:
        hash_file = _verify_hash(_get_file(src, dst, permissions))
        if hash_file != hash_expected:
            log.error("It seems that dst %s is corrupted" % dst)
            download_failures += 1
        if download_failures > download_retries:
            raise EnvironmentError("Failed to retrieve %s. "
                                   "Possible reasons - Network connectivity "
                                   "problems or incorrect hash_expected "
                                   "provided -> '%s'" %
                                   (src, hash_expected))
        else:
            log.error("Retrying download of src %s", src)

    return dst
