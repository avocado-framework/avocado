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
# Authors: Christian Herdtweck <christian.herdtweck@intra2net.com>

"""

SUMMARY
------------------------------------------------------
Utilities for file tests.


INTERFACE
------------------------------------------------------

"""

import logging
import os
from glob import iglob
from grp import getgrgid, getgrnam
from pwd import getpwnam, getpwuid
from stat import S_IMODE

LOG = logging.getLogger(__name__)


def check_owner(owner, group, file_name_pattern, check_recursive=False):
    """
    Verifies that given file belongs to given owner and group.

    :param str owner: user that owns of the file
    :param str group: group of the owner of the file
    :param str file_name_pattern: can be a glob
    :param check_recursive: if file_name_pattern matches a directory,
                            recurse into that subdir or not
    :type check_recursive: bool
    :raises: :py:class:`RuntimeError` if file has wrong owner or group
    """
    for file_name in iglob(file_name_pattern):
        actual_id = os.stat(file_name).st_uid
        if actual_id != getpwnam(owner).pw_uid:
            raise RuntimeError(
                f'file {file_name} has wrong owner '
                f'{getpwuid(actual_id).pw_name} (should be {owner})')
        actual_id = os.stat(file_name).st_gid
        if actual_id != getgrnam(group).gr_gid:
            raise RuntimeError(
                f'file {file_name} has wrong group '
                f'{getgrgid(actual_id).gr_name} (should be {group})')
        LOG.debug('checked owner %s:%s of file %s',
                  owner, group, file_name)

        if check_recursive and os.path.isdir(file_name):
            new_pattern = os.path.join(file_name,
                                       os.path.basename(file_name_pattern))
            check_owner(owner, group, new_pattern, True)


def check_permissions(perms, file_name_pattern):
    """
    Verify that a given file has a given numeric permission.

    :param int perms: best given in octal form, e.g. 0o755
    :param str file_name_pattern: can be a glob
    :raises: :py:class:`RuntimeError` if file has wrong permissions
    """
    for file_name in iglob(file_name_pattern):
        actual_perms = S_IMODE(os.stat(file_name).st_mode)
        if perms != actual_perms:
            raise RuntimeError(
                f'file {file_name} has permissions {oct(actual_perms)} '
                f'(should be {oct(perms)})!')
        LOG.debug('checked permissions %s of file %s',
                  oct(perms), file_name)
