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

from avocado.core.settings import settings


def add_tag_filter_args(parser):
    section = 'filter.by_tags'
    group = parser.add_argument_group('filtering parameters')
    settings.register_option(section=section,
                             key='tags',
                             help_msg='Filter tests based on tags',
                             action='append',
                             key_type=list,
                             default=[],
                             metavar='TAGS',
                             parser=group,
                             short_arg='-t',
                             long_arg='--filter-by-tags',
                             allow_multiple=True)

    help_msg = ('Include all tests without tags during filtering. This '
                'effectively means they will be kept in the test suite '
                'found previously to filtering.')
    settings.register_option(section=section,
                             key='include_empty',
                             default=False,
                             key_type=bool,
                             help_msg=help_msg,
                             parser=group,
                             long_arg='--filter-by-tags-include-empty',
                             allow_multiple=True)

    help_msg = ('Include all tests that do not have a matching key in its '
                'key:val tags. This effectively means those tests will be '
                'kept in the test suite found previously to filtering.')
    settings.register_option(section=section,
                             key='include_empty_key',
                             default=False,
                             key_type=bool,
                             help_msg=help_msg,
                             parser=group,
                             long_arg='--filter-by-tags-include-empty-key',
                             allow_multiple=True)
