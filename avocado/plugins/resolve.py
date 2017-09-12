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

from avocado.core.plugin_interfaces import CLICmd
from avocado.core import resolver
from avocado.core import output
from avocado.core.output import LOG_UI

from avocado.utils import astring


class Resolve(CLICmd):

    """
    Implements the avocado 'resolve' subcommand
    """

    name = 'resolve'
    description = 'Resolves test references'

    def configure(self, parser):
        parser = super(Resolve, self).configure(parser)
        parser.add_argument('reference', type=str, default=[], nargs='*',
                            help="Resolve given test references")
        parser.add_argument('-V', '--verbose',
                            action='store_true', default=False,
                            help=("Show extra information on resolution, besides "
                                  "sucessful resolutions"))

    def run(self, args):
        references = getattr(args, 'reference', [])
        resolutions = resolver.resolve(references)
        matrix, stats, tag_stats, resolution_matrix = self._get_resolution_matrix(resolutions)
        self._display(matrix, stats, tag_stats, resolution_matrix, args.verbose)

    def _get_resolution_matrix(self, resolutions):
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
                for resolution in result.resolutions:
                    type_label = resolution.kind
                    if type_label.lower() not in stats:
                        stats[type_label.lower()] = 0
                    stats[type_label.lower()] += 1
                    type_label = decorator(type_label)
                    test_matrix.append((type_label, resolution.uri))
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
                      output.TERM_SUPPORT.header_str('Test'))

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
