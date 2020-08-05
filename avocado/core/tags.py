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
# Copyright: Red Hat Inc. 2014-2019

"""
Test tags utilities module
"""


def _parse_filter_by_tags(filter_by_tags):
    """
    Parses the various filter by tags in "command line" format

    The filtering of tests usually happens my means of "--filter-by-tags"
    command line options, and many can be given.  This parses the contents
    of those into a list of must/must_not pairs, which can be used directly
    for comparisons when filtering.

    :param filter_by_tags: params in the format given to "-t/--filter-by-tags"
    :type filter_by_tags: list of str
    :returns: list of tuples with (set, set)
    """
    result = []
    for raw_tags in filter_by_tags:
        required_tags = raw_tags.split(',')
        must = set()
        must_not = set()
        for tag in required_tags:
            if tag.startswith('-'):
                must_not.add(tag[1:])
            else:
                must.add(tag)
        result.append((must, must_not))
    return result


def _must_split_flat_key_val(must):
    """
    Splits the flat and key:val tags apart

    :returns: the flat set tags and the key:val tags
    :rtype: tuple(set, dict)
    """
    key_val = {}
    flat = set()
    for i in must:
        if ':' in i:
            k, v = i.split(':', 1)
            key_val[k] = v
        else:
            flat.add(i)
    return flat, key_val


def _must_key_val_matches(must_key_vals, test_tags, include_empty_key):
    """
    Checks if the required key:vals are fulfilled by the test_tags

    :rtype: bool
    """
    key_val_test_tags = {}
    for k, v in test_tags.items():
        if v is None:
            continue
        key_val_test_tags[k] = v

    for k, v in must_key_vals.items():
        if k not in test_tags:
            if include_empty_key:
                continue
            else:
                return False
        if v not in key_val_test_tags.get(k, set()):
            return False
    return True


def filter_test_tags(test_suite, filter_by_tags, include_empty=False,
                     include_empty_key=False):
    """
    Filter the existing (unfiltered) test suite based on tags

    The filtering mechanism is agnostic to test type.  It means that
    if users request filtering by tag and the specific test type does
    not populate the test tags, it will be considered to have empty
    tags.

    :param test_suite: the unfiltered test suite
    :type test_suite: dict
    :param filter_by_tags: the list of tag sets to use as filters
    :type filter_by_tags: list of comma separated tags (['foo,bar', 'fast'])
    :param include_empty: if true tests without tags will not be filtered out
    :type include_empty: bool
    :param include_empty_key: if true tests "keys" on key:val tags will be
                              included in the filtered results
    :type include_empty_key: bool
    """
    filtered = []
    must_must_nots = _parse_filter_by_tags(filter_by_tags)

    for klass, info in test_suite:
        test_tags = info.get('tags', {})
        if not test_tags:
            if include_empty:
                filtered.append((klass, info))
            continue

        for must, must_not in must_must_nots:
            if must_not.intersection(test_tags):
                continue

            must_flat, must_key_val = _must_split_flat_key_val(must)
            if must_key_val:
                if not _must_key_val_matches(must_key_val,
                                             test_tags,
                                             include_empty_key):
                    continue

            if must_flat:
                if not must_flat.issubset(test_tags):
                    continue

            filtered.append((klass, info))
            break

    return filtered


def filter_test_tags_runnable(runnable, filter_by_tags, include_empty=False,
                              include_empty_key=False):
    """
    Filter the existing (unfiltered) test suite based on tags

    The filtering mechanism is agnostic to test type.  It means that
    if users request filtering by tag and the specific test type does
    not populate the test tags, it will be considered to have empty
    tags.

    :param test_suite: the unfiltered test suite
    :type test_suite: dict
    :param filter_by_tags: the list of tag sets to use as filters
    :type filter_by_tags: list of comma separated tags (['foo,bar', 'fast'])
    :param include_empty: if true tests without tags will not be filtered out
    :type include_empty: bool
    :param include_empty_key: if true tests "keys" on key:val tags will be
                              included in the filtered results
    :type include_empty_key: bool
    """
    must_must_nots = _parse_filter_by_tags(filter_by_tags)
    runnable_tags = runnable.tags or {}

    if not runnable_tags:
        if include_empty:
            return True

    for must, must_not in must_must_nots:
        if must_not.intersection(runnable_tags):
            continue

        must_flat, must_key_val = _must_split_flat_key_val(must)
        if must_key_val:
            if not _must_key_val_matches(must_key_val,
                                         runnable_tags,
                                         include_empty_key):
                continue

        if must_flat:
            if not must_flat.issubset(runnable_tags):
                continue

        return True

    return False
