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
# Copyright: Red Hat Inc. 2019
# Author: Cleber Rosa <crosa@redhat.com>


def add_tag_filter_args(parser):
    group = parser.add_argument_group('filtering parameters')
    group.add_argument('-t', '--filter-by-tags', metavar='TAGS',
                       action='append',
                       help='Filter tests based on tags')
    group.add_argument('--filter-by-tags-include-empty',
                       action='store_true', default=False,
                       help=('Include all tests without tags during '
                             'filtering. This effectively means they '
                             'will be kept in the test suite found '
                             'previously to filtering.'))
    group.add_argument('--filter-by-tags-include-empty-key',
                       action='store_true', default=False,
                       help=('Include all tests that do not have a '
                             'matching key in its key:val tags. This '
                             'effectively means those tests will be '
                             'kept in the test suite found previously '
                             'to filtering.'))
