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
# Copyright: 2023 IBM
# Author: Maram Srimannarayana Murthy <Maram.Srimannarayana.Murthy@ibm.com>

"""
generic utility functions.
"""


class GenericUtilityException(Exception):
    """
    Generic Utility Exception
    """


def recursive_compare_dict(dict1, dict2, level="DictKey", diff_btw_dict=None):
    """
    Difference between two dictionaries are returned
    Dict values can be a dictionary, list and value

    :rtype: List/null
    """
    if isinstance(dict1, dict) and isinstance(dict2, dict):
        if dict1.keys() != dict2.keys():
            set1 = set(dict1.keys())
            set2 = set(dict2.keys())
            diff_btw_dict.append(f"{level} + {set1-set2} - {set2-set1}")
            common_keys = set1 & set2
        else:
            common_keys = set(dict1.keys())
        for k in common_keys:
            recursive_compare_dict(
                dict1[k], dict2[k], level=f"{level}.{k}", diff_btw_dict=diff_btw_dict
            )
        return diff_btw_dict
    elif isinstance(dict1, list) and isinstance(dict2, list):
        if len(dict1) != len(dict2):
            diff_btw_dict.append(f"{level} + {len(dict1)} - {len(dict2)}")
        common_len = min(len(dict1), len(dict2))
        for i in range(common_len):
            recursive_compare_dict(
                dict1[i],
                dict2[i],
                level=f"{level}.{dict1[i]}",
                diff_btw_dict=diff_btw_dict,
            )
    else:
        if dict1 != dict2:
            diff_btw_dict.append(f"{level} - dict1 value:{dict1}, dict2 value:{dict2}")
