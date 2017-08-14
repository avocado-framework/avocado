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
# Copyright: Red Hat Inc. 2017
#
# Authors: Lukas Doktor <ldoktor@redhat.com>

"""
Jobdata compatibility layer from 36 to 52
"""

import hashlib
import itertools

from . import varianter
from . import mux


class MuxTree(mux.MuxPlugin):

    """
    Excerpt of MuxTree object in order to make it compatible with 52
    """
    pools = []
    filters = [None, None]

    def __iter__(self):
        """
        Iterates through variants
        """
        pools = []
        for pool in self.pools:
            if isinstance(pool, list):
                pools.append(itertools.chain(*pool))
            else:
                pools.append(pool)
        pools = itertools.product(*pools)
        while True:
            # TODO: Implement 2nd level filters here
            # TODO: This part takes most of the time, optimize it
            yield list(itertools.chain(*pools.next()))


class AvocadoParams(varianter.AvocadoParams):

    """
    Excerpt of original AvocadoParams in order to make it compatible
    to the 52 version of AvocadoParams
    """

    def __init__(self, leaves, test_id, tag, mux_path, default_params):
        """
        :param leaves: List of TreeNode leaves defining current variant
        :param test_id: test id
        :param tag: test tag
        :param mux_path: list of entry points
        :param default_params: dict of params used when no matches found
        """
        del tag
        super(AvocadoParams, self).__init__(leaves, test_id, mux_path,
                                            default_params)


class Mux(object):

    """
    Excerpt of Mux object in order to emulate compatible object to 52
    """
    variants = []
    _mux_path = []

    @staticmethod
    def is_parsed():
        """
        For jobdata purpose we only report True
        """
        return True

    def get_number_of_tests(self, test_suite):
        """
        :return: overall number of tests * multiplex variants
        """
        # Currently number of tests is symmetrical
        if self.variants:
            no_variants = sum(1 for _ in self.variants)
            if no_variants > 1:
                self._has_multiple_variants = True
            return (len(test_suite) * no_variants)
        else:
            return len(test_suite)

    def dump(self):
        return varianter.dump_ivariants(self.itertests)

    @staticmethod
    def _get_variant_id(variant):
        variant.sort(key=lambda x: x.path)
        fingerprint = "-".join(_.fingerprint() for _ in variant)
        return ("-".join(node.name for node in variant) + '-' +
                hashlib.sha1(fingerprint).hexdigest()[:4])

    def itertests(self):
        """
        Processes the template and yields test definition with proper params
        """
        if self.variants:  # Copy template and modify it's params
            handled = False
            for variant in self.variants:
                handled |= True
                yield {"variant": variant,
                       "variant_id": self._get_variant_id(variant),
                       "mux_path": self._mux_path}
            if not handled:   # No variants, use template
                yield {"variant": [],
                       "variant_id": None,
                       "mux_path": "/run"}
        else:   # No variants, use template
            yield {"variant": [],
                   "variant_id": None,
                   "mux_path": "/run"}
