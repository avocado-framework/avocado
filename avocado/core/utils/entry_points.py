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


def _eps_raw():
    """Call entry_points() with no arguments and return the raw result."""
    return _entry_points()


def get_entry_points_for(group):
    """Return entry points belonging to *group*, compatible with Python 3.8+.

    :param group: entry point group name (e.g. ``"avocado.plugins.cli"``)
    :type group: str
    :returns: sequence of entry points in the requested group
    """
    eps = _eps_raw()
    # Python 3.8/3.9 (el9): entry_points() returns a plain dict keyed by group
    if isinstance(eps, dict):
        return eps.get(group, [])
    # Python 3.10+: EntryPoints / SelectableGroups — use group= kwarg directly
    return _entry_points(group=group)


def get_entry_point_groups():
    """Return all registered entry point group names, compatible with Python 3.8+.

    :returns: list of group name strings
    :rtype: list
    """
    eps = _eps_raw()
    # Python 3.8/3.9: plain dict
    if isinstance(eps, dict):
        return list(eps.keys())
    # Python 3.10/3.11: SelectableGroups has .groups
    if hasattr(eps, "groups"):
        return list(eps.groups)
    # Python 3.12+: EntryPoints — collect unique group names by iterating entries
    return list({ep.group for ep in eps})
