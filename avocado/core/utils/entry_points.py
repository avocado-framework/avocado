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
# Copyright: IBM Corp. 2026
# Author: Praveen K Pandey <praveen@linux.ibm.com>

"""
Compatibility helpers for importlib.metadata.entry_points.

The entry_points() API changed across Python versions:

 Python 3.8/3.9 - returns a plain dict; group= kwarg not supported
 Python 3.10/3.11 - returns SelectableGroups; group= kwarg supported
 Python 3.12+ - returns EntryPoints; group= kwarg supported; no .get()/.groups

These helpers provide a single version-agnostic API for the whole codebase.
"""

from importlib.metadata import entry_points as _entry_points


def get_entry_points_for(group):
    """Return entry points belonging to *group*, compatible with Python 3.8+.

    :param group: entry point group name (e.g. ``"avocado.plugins.cli"``)
    :type group: str
    :returns: sequence of entry points in the requested group
    """
    try:
        # Python 3.10+: group= kwarg is supported
        return _entry_points(group=group)
    except TypeError:
        # Python 3.8/3.9: entry_points() returns a plain dict, no group= kwarg
        return _entry_points().get(group, [])


def get_entry_point_groups():
    """Return all registered entry point group names, compatible with Python 3.8+.

    :returns: list of group name strings
    :rtype: list
    """
    eps = _entry_points()
    # Python 3.8/3.9: plain dict
    if isinstance(eps, dict):
        return list(eps.keys())
    # Python 3.10/3.11: SelectableGroups has .groups
    if hasattr(eps, "groups"):
        return list(eps.groups)
    # Python 3.12+: EntryPoints — collect unique group names from entries
    return list({ep.group for ep in eps})
