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

import os

from avocado.core.plugin_interfaces import CLICmd
from avocado.core import resolver
from avocado.core import output
from avocado.core import parser_common_args
from avocado.core.output import LOG_UI
from avocado.core.tags import filter_test_tags_runnable
from avocado.utils import astring


class List(CLICmd):

    # pylint: disable=C0402
    """
    Implements the avocado 'nlist' subcommand
    """

    name = 'nlist'
    description = '*EXPERIMENTAL* list tests (runnables)'

    def configure(self, parser):
        parser = super(List, self).configure(parser)
        parser.add_argument('references', type=str, default=[], nargs='*',
                            help="Test references")
        parser.add_argument('-V', '--verbose',
                            action='store_true', default=False,
                            help=("Show extra information on resolution, besides "
                                  "sucessful resolutions"))
        parser.add_argument('--write-recipes-to-directory',
                            metavar='DIRECTORY', default=None,
                            help=('Writes runnable recipe files to a directory'))

        parser_common_args.add_tag_filter_args(parser)

    def run(self, config):
        references = config.get('references', [])
        resolutions = resolver.resolve(references)
        matrix, stats, tag_stats, resolution_matrix = self._get_resolution_matrix(config,
                                                                                  resolutions)
        self._display(matrix, stats, tag_stats, resolution_matrix, config.get('verbose'))
        recipes_directory = config.get('write_recipes_to_directory')
        if recipes_directory is not None:
            fmt = '%%0%uu.json' % len(str(len(matrix)))
            index = 1
            for resolution in resolutions:
                if resolution.result == resolver.ReferenceResolutionResult.SUCCESS:
                    for res in resolution.resolutions:
                        res.write_json(os.path.join(recipes_directory, fmt % index))
                        index += 1

    @staticmethod
    def _get_resolution_matrix(config, resolutions):
        test_matrix = []
        resolution_matrix = []
        decorator_mapping = {
            resolver.ReferenceResolutionResult.SUCCESS: output.TERM_SUPPORT.healthy_str,
            resolver.ReferenceResolutionResult.NOTFOUND: output.TERM_SUPPORT.fail_header_str,
            resolver.ReferenceResolutionResult.ERROR: output.TERM_SUPPORT.fail_header_str
            }

        # keyed by runnable kind
        stats = {}
        # by tag
        tag_stats = {}

        for result in resolutions:
            decorator = decorator_mapping.get(result.result,
                                              output.TERM_SUPPORT.warn_header_str)
            if result.resolutions:
                for runnable in result.resolutions:

                    filter_by_tags = config.get('filter_by_tags')
                    if filter_by_tags:
                        if not filter_test_tags_runnable(
                                runnable,
                                filter_by_tags,
                                config.get('filter_by_tags_include_empty'),
                                config.get('filter_by_tags_include_empty_key')):
                            continue

                    type_label = runnable.kind
                    if type_label.lower() not in stats:
                        stats[type_label.lower()] = 0
                    stats[type_label.lower()] += 1
                    type_label = decorator(type_label)

                    if config.get('verbose'):
                        tags_repr = []
                        if runnable.tags is not None:
                            for tag, vals in runnable.tags.items():
                                if tag not in tag_stats:
                                    tag_stats[tag] = 1
                                else:
                                    tag_stats[tag] += 1
                                if vals:
                                    tags_repr.append("%s(%s)" % (tag, ",".join(vals)))
                                else:
                                    tags_repr.append(tag)
                        tags_repr = ",".join(tags_repr)
                        test_matrix.append((type_label, runnable.uri, tags_repr))
                    else:
                        test_matrix.append((type_label, runnable.uri))
            else:  # assuming that empty resolutions mean a NOTFOUND, ERROR, etc
                if result.info is None:
                    result_info = ''
                else:
                    result_info = result.info
                if result.result == resolver.ReferenceResolutionResult.SUCCESS:
                    if not result_info:
                        result_info = "%i resolutions" % len(result.resolutions)
                resolution_matrix.append((decorator(result.origin),
                                          result.reference,
                                          result_info))

        return test_matrix, stats, tag_stats, resolution_matrix

    def _display(self, test_matrix, stats, tag_stats, resolution_matrix, verbose=False):
        header = None
        if verbose:
            header = (output.TERM_SUPPORT.header_str('Type'),
                      output.TERM_SUPPORT.header_str('Test'),
                      output.TERM_SUPPORT.header_str('Tags'))

        if test_matrix:
            for line in astring.iter_tabular_output(test_matrix,
                                                    header=header,
                                                    strip=True):
                LOG_UI.debug(line)

        if verbose:

            if stats:
                LOG_UI.info("")
                LOG_UI.info("TEST TYPES SUMMARY")
                LOG_UI.info("==================")
                for key in sorted(stats):
                    LOG_UI.info("%s: %s", key, stats[key])

            if tag_stats:
                LOG_UI.info("")
                LOG_UI.info("TEST TAGS SUMMARY")
                LOG_UI.info("=================")
                for key in sorted(tag_stats):
                    LOG_UI.info("%s: %s", key, tag_stats[key])

            if resolution_matrix:
                resolution_header = (output.TERM_SUPPORT.header_str('Resolver'),
                                     output.TERM_SUPPORT.header_str('Reference'),
                                     output.TERM_SUPPORT.header_str('Info'))
                LOG_UI.info("")
                for line in astring.iter_tabular_output(resolution_matrix,
                                                        header=resolution_header,
                                                        strip=True):
                    LOG_UI.info(line)
