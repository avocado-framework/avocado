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
# Copyright: Red Hat Inc. 2021
# Author: Cleber Rosa <crosa@redhat.com>
__doc__ = """
Module to read UNIX ar files
"""

import struct

#: The first eight bytes of all AR archives
MAGIC = b"!<arch>\n"

#: The header for each file in the archive
FILE_HEADER_FMT = "16s12s6s6s8s10s2c"
FILE_HEADER_SIZE = struct.calcsize(FILE_HEADER_FMT)


class ArMember:
    """A member of an UNIX ar archive."""

    def __init__(self, identifier, size, offset):
        self.identifier = identifier
        self.size = size
        self.offset = offset

    def __repr__(self):
        return (
            f'<ArMember "{self.identifier}" size={int(self.size)} '
            f"offset={int(self.offset)}>"
        )


class Ar:
    """An UNIX ar archive iterator.

    It reads ar archive file and iterates over the members in form of :class:`autils.archive.ar.ArMember`
    """

    def __init__(self, path):
        self._path = path
        self._file = None
        self._position = None
        self._valid = False

    def __enter__(self):
        self._file = open(self._path, "rb")
        return self._file

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self._file.close()

    def is_valid(self):
        """Checks if a file looks like an AR archive.

        :return: If file looks like an AR archive
        :rtype: bool
        """
        with self as open_file:
            return open_file.read(8) == MAGIC

    def __iter__(self):
        self._position = 8
        self._valid = self.is_valid()
        return self

    def __next__(self):
        if not self._valid:
            raise StopIteration

        with self as open_file:
            open_file.seek(self._position)
            try:
                member = struct.unpack(
                    FILE_HEADER_FMT, open_file.read(FILE_HEADER_SIZE)
                )
            except struct.error as exc:
                raise StopIteration from exc

            # No support for extended file names
            identifier = member[0].decode("ascii").strip()
            # from bytes containing a decimal to int
            size = int(member[5].decode("ascii").strip())

            data_position = self._position + FILE_HEADER_SIZE
            # All data sections is aligned at 2 bytes
            data_position += data_position % 2
            self._position += FILE_HEADER_SIZE + size
            return ArMember(identifier, size, data_position)

    def list(self):
        """List the members in the archive.

        :return: List the names of the members in the archive
        :rtype: list
        """
        return [member.identifier for member in self]

    def read_member(self, identifier):
        """Reads the data for the given member identifier.

        :param identifier: Archive member name.
        :type identifier: str
        :return: data for the given member
        :rtype: bytes or None
        """
        for member in self:
            if identifier == member.identifier:
                with self as open_file:
                    open_file.seek(member.offset)
                    return open_file.read(member.size)
        return None


# pylint: disable=wrong-import-position
from avocado.utils.deprecation import log_deprecation

log_deprecation.warning("ar")
