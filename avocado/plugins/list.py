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

from avocado.core import exit_codes, loader, output, parser_common_args
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.settings import settings
from avocado.core.suite import TestSuite
from avocado.core.test import Test
from avocado.utils import astring


def _get_test_tags(test):
    """Return a list of all tags of a test as string."""
    params = test[1]
    tags_repr = []
    for tag, values in params.get('tags', {}).items():
        if values:
            tags_repr.append("%s(%s)" % (tag, ",".join(values)))
        else:
            tags_repr.append(tag)
    return ",".join(tags_repr)


class List(CLICmd):

    """
    Implements the avocado 'list' subcommand
    """

    name = 'list'
    description = 'List available tests'

    def _display(self, test_matrix, suite, verbose=False):
        header = None
        if verbose:
            header = (output.TERM_SUPPORT.header_str('Type'),
                      output.TERM_SUPPORT.header_str('Test'),
                      output.TERM_SUPPORT.header_str('Tag(s)'))

        for line in astring.iter_tabular_output(test_matrix, header=header,
                                                strip=True):
            LOG_UI.debug(line)

        if verbose:
            LOG_UI.info("")
            LOG_UI.info("TEST TYPES SUMMARY")
            LOG_UI.info("==================")
            for key in sorted(suite.stats):
                LOG_UI.info("%s: %s", key.upper(), suite.stats[key])

            if suite.tags_stats:
                LOG_UI.info("")
                LOG_UI.info("TEST TAGS SUMMARY")
                LOG_UI.info("=================")
                for key in sorted(suite.tags_stats):
                    LOG_UI.info("%s: %s", key, suite.tags_stats[key])

    def _get_test_matrix(self, test_suite, verbose=False):
        test_matrix = []

        type_label_mapping = loader.loader.get_type_label_mapping()
        decorator_mapping = loader.loader.get_decorator_mapping()

        for cls, params in test_suite:
            if isinstance(cls, str):
                cls = Test
            type_label = type_label_mapping[cls]
            decorator = decorator_mapping[cls]
            type_label = decorator(type_label)

            if verbose:
                test_matrix.append((type_label,
                                    params['name'],
                                    _get_test_tags((cls, params))))
            else:
                test_matrix.append((type_label, params['name']))

        return test_matrix

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
        loader.add_loader_options(parser, 'list')
        parser_common_args.add_tag_filter_args(parser)

    def run(self, config):
        # Current Runner
        verbose = config.get('core.verbose')
        config['run.references'] = config.get('list.references')
        config['run.test_runner'] = config.get('run.test_runner')
        try:
            suite = TestSuite.from_config(config)
            test_matrix = self._get_test_matrix(suite.tests, verbose)
            return self._display(test_matrix, suite, verbose)
        except KeyboardInterrupt:
            LOG_UI.error('Command interrupted by user...')
            return exit_codes.AVOCADO_FAIL
