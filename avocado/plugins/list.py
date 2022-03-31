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

import json
import os

from avocado.core import exit_codes, parser_common_args
from avocado.core.output import LOG_UI, TERM_SUPPORT
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.resolver import ReferenceResolutionResult
from avocado.core.settings import settings
from avocado.core.suite import TestSuite
from avocado.utils.astring import iter_tabular_output


def _get_tags_as_string(tags):
    """Return a list of all tags but in a string format for output."""
    tags_repr = []
    for tag, values in tags.items():
        if values:
            tags_repr.append(f"{tag}({','.join(values)})")
        else:
            tags_repr.append(tag)
    return ",".join(tags_repr)


class List(CLICmd):

    """
    Implements the avocado 'list' subcommand
    """

    name = 'list'
    description = 'List available tests'

    @staticmethod
    def _prepare_matrix_for_display(matrix, verbose=False):
        colored_matrix = []
        for item in matrix:
            cls = item[0]
            type_label = TERM_SUPPORT.healthy_str(cls)
            if verbose:
                colored_matrix.append((type_label, item[1],
                                       _get_tags_as_string(item[2] or {})))
            else:
                colored_matrix.append((type_label, item[1]))
        return colored_matrix

    def _display(self, suite, matrix):
        header = None
        verbose = suite.config.get('core.verbose')
        if verbose:
            header = (TERM_SUPPORT.header_str('Type'),
                      TERM_SUPPORT.header_str('Test'),
                      TERM_SUPPORT.header_str('Tag(s)'))

        # Any kind of color, string format and term specific should be applied
        # only during output/display phase. So this seems to be a better place
        # for this:
        matrix = self._prepare_matrix_for_display(matrix, verbose)

        for line in iter_tabular_output(matrix,
                                        header=header,
                                        strip=True):
            LOG_UI.debug(line)

        self._display_extra(suite, verbose)

    @staticmethod
    def _display_extra(suite, verbose=True):
        """Display extra data when in verbose mode."""
        if not verbose:
            return

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
    def _get_resolution_matrix(suite):
        """Used for resolver."""
        test_matrix = []
        verbose = suite.config.get('core.verbose')
        for runnable in suite.tests:

            if verbose:
                tags = runnable.tags or {}
                test_matrix.append((runnable.kind, runnable.uri, tags))
            else:
                test_matrix.append((runnable.kind, runnable.uri))
        return test_matrix

    @staticmethod
    def _save_to_json(matrix, filename, verbose=False):
        result = []
        type_label_mapping = {}

        for line in matrix:
            try:
                test_type = type_label_mapping[line[0]]
            except KeyError:
                test_type = line[0]
            if verbose:
                tags = line[2] or {}
                result.append({'Type': test_type,
                               'Test': line[1],
                               'Tags': {k: list(v or {})
                                        for k, v in tags.items()}})
            else:
                result.append({'Type': test_type,
                               'Test': line[1]})
        if filename == '-':
            LOG_UI.debug(json.dumps(result, indent=4))
        else:
            with open(filename, 'w', encoding='utf-8') as fp:
                json.dump(result, fp, indent=4)

    @staticmethod
    def save_recipes(suite, directory, matrix_len):
        fmt = f'%0{len(str(matrix_len))}u.json'
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
        parser = super().configure(parser)
        settings.add_argparser_to_option(namespace='resolver.references',
                                         nargs='*',
                                         metavar='TEST_REFERENCE',
                                         parser=parser,
                                         positional_arg=True,
                                         long_arg=None,
                                         allow_multiple=True)

        help_msg = ('Writes runnable recipe files to a directory.')
        settings.register_option(section='list.recipes',
                                 key='write_to_directory',
                                 default=None,
                                 metavar='DIRECTORY',
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--write-recipes-to-directory')

        help_msg = 'Writes output to a json file.'
        settings.register_option(section='list',
                                 key='write_to_json_file',
                                 default=None,
                                 metavar='JSON_FILE',
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--json')

        parser_common_args.add_tag_filter_args(parser)

    def run(self, config):
        verbose = config.get('core.verbose')
        write_to_json_file = config.get('list.write_to_json_file')
        config['run.ignore_missing_references'] = True
        config['run.test_runner'] = 'nrunner'
        try:
            suite = TestSuite.from_config(config)
            matrix = self._get_resolution_matrix(suite)
            self._display(suite, matrix)

            directory = config.get('list.recipes.write_to_directory')
            if directory is not None:
                self.save_recipes(suite, directory, len(matrix))
            if write_to_json_file:
                self._save_to_json(matrix, write_to_json_file, verbose)
        except KeyboardInterrupt:
            LOG_UI.error('Command interrupted by user...')
            return exit_codes.AVOCADO_FAIL
