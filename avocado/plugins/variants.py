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
# Copyright: Red Hat Inc. 2013-2014,2016
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>
# Author: Lukas Doktor <ldoktor@redhat.com>

import json
import sys

from avocado.core import exit_codes
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.settings import settings
from avocado.core.varianter import Varianter

_VERBOSITY_LEVELS = {"none": 0, "brief": 1, "normal": 2, "verbose": 3,
                     "full": 4, "max": 99}


def map_verbosity_level(level):
    if level.isdigit():
        return int(level)
    level = level.lower()
    if level in _VERBOSITY_LEVELS:
        return _VERBOSITY_LEVELS[level]
    else:
        raise ValueError


class Variants(CLICmd):

    """
    Implements "variants" command to visualize/debug test variants and params
    """

    name = 'variants'
    description = "Tool to analyze and visualize test variants and params"

    def configure(self, parser):
        parser = super(Variants, self).configure(parser)
        verbosity_levels = ("(positive integer - 0, 1, ... - or %s)"
                            % ", ".join(sorted(_VERBOSITY_LEVELS,
                                               key=lambda _: _VERBOSITY_LEVELS[_])))

        help_msg = 'Verbosity of the variants summary. ' + verbosity_levels
        settings.register_option(section='variants',
                                 key='summary',
                                 key_type=map_verbosity_level,
                                 default=0,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--summary',
                                 metavar='SUMMARY')

        help_msg = 'Verbosity of the list of variants. ' + verbosity_levels
        settings.register_option(section='variants',
                                 key='variants',
                                 key_type=map_verbosity_level,
                                 default=1,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--variants',
                                 metavar='VARIANTS')

        help_msg = ('[obsoleted by --variants] Shows the node content '
                    '(variables)')
        settings.register_option(section='variants',
                                 key='contents',
                                 key_type=bool,
                                 default=False,
                                 parser=parser,
                                 help_msg=help_msg,
                                 short_arg='-c',
                                 long_arg='--contents')

        help_msg = 'Dump the Variants to a JSON serialized file'
        settings.register_option(section='variants',
                                 key='json_variants_dump',
                                 help_msg=help_msg,
                                 default=None,
                                 parser=parser,
                                 long_arg='--json-variants-dump',
                                 metavar='FILE')

        env_parser = parser.add_argument_group("environment view options")

        help_msg = 'Use debug implementation to gather more information.'
        settings.register_option(section='variants',
                                 key='debug',
                                 help_msg=help_msg,
                                 parser=env_parser,
                                 key_type=bool,
                                 default=False,
                                 long_arg='--debug',
                                 short_arg='-d')

        tree_parser = parser.add_argument_group("tree view options")

        help_msg = ('[obsoleted by --summary] Shows the multiplex tree '
                    'structure')
        settings.register_option(section='variants',
                                 key='tree',
                                 key_type=bool,
                                 default=False,
                                 help_msg=help_msg,
                                 parser=tree_parser,
                                 long_arg='--tree',
                                 short_arg='-t')

        help_msg = '[obsoleted by --summary] Show the inherited values'
        settings.register_option(section='variants',
                                 key='inherit',
                                 key_type=bool,
                                 help_msg=help_msg,
                                 parser=tree_parser,
                                 default=False,
                                 short_arg='-i',
                                 long_arg='--inherit')

    def run(self, config):
        tree = config.get('variants.tree')
        summary = config.get('variants.summary')
        variants = config.get('variants.variants')
        contents = config.get('variants.contents')
        inherit = config.get('variants.inherit')

        err = None
        if tree and config.get('variants.debug'):
            err = "Option --tree is incompatible with --debug."
        elif not tree and inherit:
            err = "Option --inherit can be only used with --tree"
        if err:
            LOG_UI.error(err)
            sys.exit(exit_codes.AVOCADO_FAIL)
        varianter = Varianter()
        try:
            varianter.parse(config)
        except (IOError, ValueError) as details:
            LOG_UI.error("Unable to parse varianter: %s", details)
            sys.exit(exit_codes.AVOCADO_FAIL)
        use_utf8 = config.get("runner.output.utf8")
        # Parse obsolete options (unsafe to combine them with new args)
        if tree:
            variants = 0
            summary += 1
            if contents:
                summary += 1
            if inherit:
                summary += 2
        else:
            if contents:
                variants += 2

        json_variants_dump = config.get('variants.json_variants_dump')
        # Export the serialized variants
        if json_variants_dump is not None:
            try:
                with open(json_variants_dump, 'w') as variants_file:
                    json.dump(varianter.dump(), variants_file)
            except IOError:
                LOG_UI.error("Cannot write %s", json_variants_dump)
                sys.exit(exit_codes.AVOCADO_FAIL)

        # Produce the output
        lines = varianter.to_str(summary=summary,
                                 variants=variants,
                                 use_utf8=use_utf8)
        for line in lines.splitlines():
            LOG_UI.debug(line)

        sys.exit(exit_codes.AVOCADO_ALL_OK)
