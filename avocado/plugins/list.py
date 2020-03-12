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
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

import sys

from avocado.core import exit_codes, output
from avocado.core import loader
from avocado.core import test
from avocado.core import tags
from avocado.core import parser_common_args
from avocado.core.output import LOG_UI
from avocado.core.future.settings import settings
from avocado.core.plugin_interfaces import CLICmd
from avocado.utils import astring


class TestLister:

    """
    Lists available test modules
    """

    def __init__(self, args):
        try:
            loader.loader.load_plugins(args)
        except loader.LoaderError as details:
            sys.stderr.write(str(details))
            sys.stderr.write('\n')
            sys.exit(exit_codes.AVOCADO_FAIL)
        self.args = args

    def _extra_listing(self):
        loader.loader.get_extra_listing()

    def _get_test_suite(self, paths):
        if self.args.get('core.verbose'):
            which_tests = loader.DiscoverMode.ALL
        else:
            which_tests = loader.DiscoverMode.AVAILABLE
        try:
            return loader.loader.discover(paths,
                                          which_tests=which_tests)
        except loader.LoaderUnhandledReferenceError as details:
            LOG_UI.error(str(details))
            sys.exit(exit_codes.AVOCADO_FAIL)

    def _get_test_matrix(self, test_suite):
        test_matrix = []

        type_label_mapping = loader.loader.get_type_label_mapping()
        decorator_mapping = loader.loader.get_decorator_mapping()

        stats = {}
        tag_stats = {}
        for value in type_label_mapping.values():
            stats[value.lower()] = 0

        for cls, params in test_suite:
            if isinstance(cls, str):
                cls = test.Test
            type_label = type_label_mapping[cls]
            decorator = decorator_mapping[cls]
            stats[type_label.lower()] += 1
            type_label = decorator(type_label)

            if self.args.get('core.verbose'):
                if 'tags' in params:
                    tgs = params['tags']
                else:
                    tgs = {}
                tags_repr = []
                for tag, vals in tgs.items():
                    if tag not in tag_stats:
                        tag_stats[tag] = 1
                    else:
                        tag_stats[tag] += 1
                    if vals:
                        tags_repr.append("%s(%s)" % (tag, ",".join(vals)))
                    else:
                        tags_repr.append(tag)
                tags_repr = ",".join(tags_repr)
                test_matrix.append((type_label, params['name'], tags_repr))
            else:
                test_matrix.append((type_label, params['name']))

        return test_matrix, stats, tag_stats

    def _display(self, test_matrix, stats, tag_stats):
        header = None
        if self.args.get('core.verbose'):
            header = (output.TERM_SUPPORT.header_str('Type'),
                      output.TERM_SUPPORT.header_str('Test'),
                      output.TERM_SUPPORT.header_str('Tag(s)'))

        for line in astring.iter_tabular_output(test_matrix, header=header,
                                                strip=True):
            LOG_UI.debug(line)

        if self.args.get('core.verbose'):
            LOG_UI.info("")
            LOG_UI.info("TEST TYPES SUMMARY")
            LOG_UI.info("==================")
            for key in sorted(stats):
                LOG_UI.info("%s: %s", key.upper(), stats[key])

            if tag_stats:
                LOG_UI.info("")
                LOG_UI.info("TEST TAGS SUMMARY")
                LOG_UI.info("=================")
                for key in sorted(tag_stats):
                    LOG_UI.info("%s: %s", key, tag_stats[key])

    def _list(self):
        self._extra_listing()
        test_suite = self._get_test_suite(self.args.get('list.references'))
        if self.args.get('filter_by_tags', False):
            test_suite = tags.filter_test_tags(
                test_suite,
                self.args.get('filter_by_tags'),
                self.args.get('filter_by_tags_include_empty'),
                self.args.get('filter_by_tags_include_empty_key'))
        test_matrix, stats, tag_stats = self._get_test_matrix(test_suite)
        self._display(test_matrix, stats, tag_stats)

    def list(self):
        try:
            self._list()
        except KeyboardInterrupt:
            LOG_UI.error('Command interrupted by user...')
            return exit_codes.AVOCADO_FAIL


class List(CLICmd):

    """
    Implements the avocado 'list' subcommand
    """

    name = 'list'
    description = 'List available tests'

    def configure(self, parser):
        """
        Add the subparser for the list action.

        :param parser: The Avocado command line application parser
        :type parser: :class:`avocado.core.parser.ArgumentParser`
        """
        parser = super(List, self).configure(parser)
        help_msg = ('List of test references (aliases or paths). If empty, '
                    'Avocado will list tests on the configured test source, '
                    '(see "avocado config --datadir") Also, if there are '
                    'other test loader plugins active, tests from those '
                    'plugins might also show up (behavior may vary among '
                    'plugins)')
        settings.register_option(section='list',
                                 key='references',
                                 default=[],
                                 nargs='*',
                                 key_type=list,
                                 help_msg=help_msg,
                                 parser=parser,
                                 positional_arg=True)
        loader.add_loader_options(parser)
        parser_common_args.add_tag_filter_args(parser)

    def run(self, config):
        test_lister = TestLister(config)
        return test_lister.list()
