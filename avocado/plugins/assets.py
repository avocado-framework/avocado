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
# Authors: Willian Rampazzo <willianr@redhat.com>

import ast
import errno
import json
import os
import tempfile

from avocado.utils import process
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd


TEST_TEMPLATE = r"""
from avocado import Test

class FetchAssets(Test):
    def test_fetch_assets(self):
{fetch_assets}
"""


class FetchAssetHandler(ast.NodeVisitor):

    def __init__(self, file_name):
        self.file_name = file_name
        # Right now, the class handles just 'fetch_assets' call.
        # In the future, it can be extended to search for other call patterns.
        self.pattern = 'fetch_asset'
        self.calls = []
        self.result = None

        # create Abstract Syntax Tree from test source file
        with open(self.file_name) as source_file:
            self.tree = ast.parse(source_file.read(), self.file_name)

        # build calls list
        self.visit(self.tree)
    # __init__()

    def _build_call(self, node):
        """
        Build the call string from ast nodes.
        :param node: Call root node
        :type node: ast.Call
        :return: Call prepared to be executed into a test class
        :rtype: str
        """
        # we handle code indentation
        call = "        self." + node.func.attr + "("
        for a in node.args:
            if isinstance(a, ast.Name):
                return None
            elif isinstance(a, ast.Str):
                call = call + '"' + ast.literal_eval(a) + '", '
        for k in node.keywords:
            call = call + k.arg + "="
            if isinstance(k.value, ast.Name):
                return None
            elif isinstance(k.value, ast.Str):
                call = call + '"' + ast.literal_eval(k.value) + '", '
        # remove last comma and add parenthesis
        call = call[:-2] + ")\n"

        return call
    # _build_call()

    def visit_Call(self, node):
        """
        Visit calls and build call string if call matches the pattern
        :param node: (Sub)Tree root to start the parse
        :type node: ast.*
        """
        if isinstance(node.func, ast.Attribute):
            if self.pattern in node.func.attr:
                call = self._build_call(node)
                if call is not None:
                    self.calls.append(call)
    # visit_call()

    def fetcher(self):
        """
        Build an intrumented avocado test with all fetch_asset calls and
        execute it.
        """
        # build raw code from list of calls, if available
        if len(self.calls) > 0:
            rcalls = ""
            for call in self.calls:
                rcalls = rcalls + call
        else:
            LOG_UI.debug('No supported assets found to fetch from %s'
                         % self.file_name)
            return

        # temporary test source file
        fetch_test = tempfile.NamedTemporaryFile(suffix=".py")
        fetch_test.write(TEST_TEMPLATE.format(fetch_assets=rcalls).encode())
        fetch_test.flush()

        # run teporary test
        LOG_UI.debug('Fetching assets from %s' % self.file_name)
        self.result = process.run("avocado run --json - %s" % fetch_test.name,
                                  ignore_status=True)
        fetch_test.close()

        # check if test ran without problems
        fetch_test_stdout = json.loads(self.result.stdout)
        if (self.result.exit_status != 0
                or fetch_test_stdout['pass'] != fetch_test_stdout['total']):
            LOG_UI.error('%s Check %s for more details.' % (
                fetch_test_stdout['tests'][0]['fail_reason'],
                fetch_test_stdout['tests'][0]['logfile']))
    # fetcher()
# FetchAssetHandler()


class Assets(CLICmd):
    """
    Implements the avocado 'assets' subcommand
    """
    name = 'assets'
    description = 'Manage assets'

    def configure(self, parser):
        """
        Add the subparser for the assets action.

        :param parser: Main test runner parser.
        """
        parser = super(Assets, self).configure(parser)

        subcommands = parser.add_subparsers(dest='assets_subcommand')
        subcommands.required = True

        fetch_subcommand_parser = subcommands.add_parser('fetch',
                                help='Fetch assets from test source'\
                                ' or config file if it\'s not already in the'\
                                ' cache')
        fetch_subcommand_parser.add_argument('references', type=str,
                                             default=[], nargs='*',
                                             metavar='TEST_REFERENCE',
                                             help='List of test references')
    # configure()

    def run(self, config):
        subcommand = config.get('assets_subcommand')

        if subcommand == 'fetch':

            # check if we have something to work on
            if len(config['references']) < 1:
                LOG_UI.error('No test references provided nor any other' \
                               ' arguments.')

            # fetch assets from instrumented tests
            fetch_asset_handler = {}
            for test_file in config['references']:
                if os.path.isfile(test_file) and test_file.endswith('.py'):
                    fetch_asset_handler[test_file] = FetchAssetHandler(
                                                                    test_file)
                    fetch_asset_handler[test_file].fetcher()
                else:
                    LOG_UI.warn('No such file or file not supported: %s',
                                test_file)
    # run()

