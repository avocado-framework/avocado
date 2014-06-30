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
# Copyright: Red Hat Inc. 2013-2014
# Authors: Lucas Meneghel Rodrigues <lmr@redhat.com>
#          Ruda Moura <rmoura@redhat.com>

import os
import re

from avocado import multiplex, multiplex_parser

class Parser(object):

    def __init__(self, filename):
        config_path = os.path.abspath(filename)
        with open(config_path, 'r') as config_file_obj:
            self.data_structure = multiplex_parser.read_yaml(config_file_obj)

    def _get_leaves(self):
        for x in multiplex_parser.walk(self.data_structure):
            if isinstance(x[1], dict):
                continue
            path = '/%s/%s' % ('/'.join(x[0]), x[1])
            yield path, x[1]

    def create_variants(self, filter_only=None):
        leaves = self._get_leaves()
        self.variants = multiplex.multiplex(leaves, filter_only=filter_only)

    def get_variants_with_parameters(self, test_url):
        filter_url = '/tests/%s/' % test_url
        self.create_variants(filter_only=[filter_url])
        for variant in self.variants:
            res = {}
            keys = []
            for arg in variant:
                key = arg[0][len(filter_url):]
                keys.append(key.replace('/', '_'))
                key = multiplex.parent(key)
                res[key] = arg[1]
            shortname = '%s.%s' % (test_url, '.'.join(keys))
            res['shortname'] = shortname
            yield res
