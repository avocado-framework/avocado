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
# Copyright: Red Hat Inc. 2024
# Authors: Jan Richter <jarcihte@redhat.com>


class Dependency:
    """
    Data holder for dependency.
    """

    def __init__(self, kind=None, uri=None, args=(), kwargs=None):
        self._kind = kind
        self._uri = uri
        self._args = args
        self._kwargs = kwargs or {}

    @property
    def kind(self):
        return self._kind

    @property
    def uri(self):
        return self._uri

    @property
    def args(self):
        return self._args

    @property
    def kwargs(self):
        return self._kwargs

    def __hash__(self):
        return hash(
            (
                self.kind,
                self.uri,
                tuple(sorted(self.args)),
                tuple(sorted(self.kwargs.items())),
            )
        )

    def __eq__(self, other):
        if isinstance(other, Dependency):
            return hash(self) == hash(other)
        return False

    @classmethod
    def from_dictionary(cls, dictionary):
        return cls(
            dictionary.pop("type", None),
            dictionary.pop("uri", None),
            dictionary.pop("args", ()),
            dictionary,
        )
