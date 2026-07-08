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

    On Python 3.9 (el9), ``importlib.metadata.entry_points()`` is called with
    no arguments and returns a plain dict.  In RPM build environments the same
    package version can appear in more than one ``dist-info`` directory on
    ``sys.path`` (e.g. both the system install and the BUILDROOT install), which
    causes the same entry point to be listed multiple times in that dict.  The
    deduplication below guards against loading a plugin class more than once,
    which would otherwise cause every plugin method to be invoked twice per
    event (leading to errors like ``FileExistsError`` in the bystatus plugin).

    :param group: entry point group name (e.g. ``"avocado.plugins.cli"``)
    :type group: str
    :returns: sequence of entry points in the requested group, deduplicated
    """
    eps = _eps_raw()
    # Python 3.8/3.9 (el9): entry_points() returns a plain dict keyed by group
    if isinstance(eps, dict):
        seen = set()
        result = []
        for ep in eps.get(group, []):
            # (name, value) uniquely identifies a plugin regardless of which
            # dist-info directory it was discovered from.
            key = (ep.name, ep.value)
            if key not in seen:
                seen.add(key)
                result.append(ep)
        return result
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
