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
# Author: Beraldo Leal <bleal@redhat.com>

import os

from avocado.core import exit_codes, loader, parser_common_args
from avocado.core.output import LOG_UI, TERM_SUPPORT
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.resolver import ReferenceResolutionResult
from avocado.core.settings import settings
from avocado.core.suite import TestSuite
from avocado.core.test import Test
from avocado.utils.astring import iter_tabular_output


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

    def _display(self, suite, matrix):
        header = None
        verbose = suite.config.get('core.verbose')
        if verbose:
            header = (TERM_SUPPORT.header_str('Type'),
                      TERM_SUPPORT.header_str('Test'),
                      TERM_SUPPORT.header_str('Tag(s)'))

        for line in iter_tabular_output(matrix,
                                        header=header,
                                        strip=True):
            LOG_UI.debug(line)

        if verbose:
            if suite.resolutions:
                resolution_header = (TERM_SUPPORT.header_str('Resolver'),
                                     TERM_SUPPORT.header_str('Reference'),
                                     TERM_SUPPORT.header_str('Info'))
                LOG_UI.info("")

                mapping = {
                  ReferenceResolutionResult.SUCCESS: TERM_SUPPORT.healthy_str,
                  ReferenceResolutionResult.NOTFOUND: TERM_SUPPORT.fail_header_str,
                  ReferenceResolutionResult.ERROR: TERM_SUPPORT.fail_header_str
                }
                resolution_matrix = []
                for r in suite.resolutions:
                    decorator = mapping.get(r.result,
                                            TERM_SUPPORT.warn_header_str)
                    if r.result == ReferenceResolutionResult.SUCCESS:
                        continue
                    resolution_matrix.append((decorator(r.origin),
                                              r.reference,
                                              r.info or ''))

                for line in iter_tabular_output(resolution_matrix,
                                                header=resolution_header,
                                                strip=True):
                    LOG_UI.info(line)

            LOG_UI.info("")
            LOG_UI.info("TEST TYPES SUMMARY")
            LOG_UI.info("==================")
            for key in sorted(suite.stats):
                LOG_UI.info("%s: %s", key, suite.stats[key])

            if suite.tags_stats:
                LOG_UI.info("")
                LOG_UI.info("TEST TAGS SUMMARY")
                LOG_UI.info("=================")
                for key in sorted(suite.tags_stats):
                    LOG_UI.info("%s: %s", key, suite.tags_stats[key])

    @staticmethod
    def _get_test_matrix(suite):
        """Used for loader."""
        test_matrix = []

        type_label_mapping = loader.loader.get_type_label_mapping()
        decorator_mapping = loader.loader.get_decorator_mapping()

        verbose = suite.config.get('core.verbose')
        for cls, params in suite.tests:
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

    @staticmethod
    def _get_resolution_matrix(suite):
        """Used for resolver."""
        test_matrix = []
        verbose = suite.config.get('core.verbose')
        for test in suite.tests:
            runnable = test.runnable

            type_label = TERM_SUPPORT.healthy_str(runnable.kind)

            if verbose:
                tags_repr = []
                tags = runnable.tags or {}
                for tag, vals in tags.items():
                    if vals:
                        tags_repr.append("%s(%s)" % (tag,
                                                     ",".join(vals)))
                    else:
                        tags_repr.append(tag)
                tags_repr = ",".join(tags_repr)
                test_matrix.append((type_label, runnable.uri, tags_repr))
            else:
                test_matrix.append((type_label, runnable.uri))
        return test_matrix

    @staticmethod
    def save_recipes(suite, directory, matrix_len):
        fmt = '%%0%uu.json' % len(str(matrix_len))
        index = 1
        for resolution in suite.resolutions:
            if resolution.result == ReferenceResolutionResult.SUCCESS:
                for res in resolution.resolutions:
                    res.write_json(os.path.join(directory, fmt % index))
                    index += 1

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

        help_msg = ('What is the method used to detect tests? If --resolver '
                    'used, Avocado will use the Next Runner Resolver method. '
                    'If not the legacy one will be used.')
        settings.register_option(section='list',
                                 key='resolver',
                                 key_type=bool,
                                 default=False,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--resolver')

        help_msg = ('Writes runnable recipe files to a directory. Valid only '
                    'when using --resolver.')
        settings.register_option(section='list.recipes',
                                 key='write_to_directory',
                                 default=None,
                                 metavar='DIRECTORY',
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--write-recipes-to-directory')

        parser_common_args.add_tag_filter_args(parser)

    def run(self, config):
        runner = 'nrunner' if config.get('list.resolver') else 'runner'
        config['run.references'] = config.get('list.references')
        config['run.ignore_missing_references'] = True
        config['run.test_runner'] = runner
        try:
            suite = TestSuite.from_config(config)
            if runner == 'nrunner':
                matrix = self._get_resolution_matrix(suite)
                self._display(suite, matrix)

                directory = config.get('list.recipes.write_to_directory')
                if directory is not None:
                    self.save_recipes(suite, directory, len(matrix))
            else:
                matrix = self._get_test_matrix(suite)
                self._display(suite, matrix)
        except KeyboardInterrupt:
            LOG_UI.error('Command interrupted by user...')
            return exit_codes.AVOCADO_FAIL
