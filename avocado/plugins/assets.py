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

"""
Assets subcommand
"""

import ast
import os

from avocado.core import data_dir
from avocado.core import exit_codes
from avocado.core import safeloader
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.utils.asset import Asset
from avocado.utils import data_structures


class FetchAssetHandler(ast.NodeVisitor):  # pylint: disable=R0902
    """
    Handles the parsing of instrumented tests for `fetch_asset` statements.
    """

    def __init__(self, file_name):
        self.file_name = file_name
        self.pattern = 'fetch_asset'
        self.asgmts = {}
        self.calls = []

        # hold current class and current method to make sure we have the
        # correct context for the assignment statement.
        # at this time, module constants and class attributes are discarded.
        self.current_klass = None
        self.current_method = None

        # check if we have valid instrumented tests
        # discards disabled tests
        self.tests = safeloader.find_avocado_tests(self.file_name)[0]

        # create Abstract Syntax Tree from test source file
        with open(self.file_name) as source_file:
            self.tree = ast.parse(source_file.read(), self.file_name)

        # build list of keyword arguments from calls that match pattern
        self.visit(self.tree)

    def _parse_args(self, node):
        """
        Parse the AST fetch_asset node and build the arguments dictionary.
        :param node: AST node to be evaluated
        :type node: ast.Attribute
        :returns: keywords and arguments from a fetch_asset call.
        :rtype: dict
        """
        args = []
        # variables to make lines shorter
        cur_klass = self.current_klass
        cur_method = self.current_method

        # parse args from call
        for arg in node.args:
            # handle string args
            if isinstance(arg, ast.Str):
                args.append(arg.s)
            # handle variable args
            elif isinstance(arg, ast.Name):
                # look for assignments at method
                if arg.id in self.asgmts[cur_klass][cur_method]:
                    args.append(self.asgmts[cur_klass][cur_method][arg.id])
                # right now we support just one level of variable as argument,
                # with a pure string assignment, in the same context,
                # just like `name = 'file.zip'`
                else:
                    return None

        # starts building the keywords dictionary for the asset.Asset()
        # class constructor.
        keywords = ["name", "asset_hash", "algorithm", "locations", "expire"]
        fetch_args = dict(zip(keywords, args))

        # parse keyword args for call
        for kwarg in node.keywords:
            # variable to make lines shorter
            kword = kwarg.arg
            # handle `keyword = string`
            if isinstance(kwarg.value, ast.Str):
                fetch_args[kword] = kwarg.value.s
            # handle `keyword = variable`
            elif isinstance(kwarg.value, ast.Name):
                name = kwarg.value.id
                # look for assignments at method
                if name in self.asgmts[cur_klass][cur_method]:
                    fetch_args[kword] = self.asgmts[cur_klass][cur_method][name]
                # right now we support just one level of variable as argument,
                # with a pure string assignment, in the same context,
                # just like `name = 'file.zip'`
                else:
                    return None

        # Fill empty keywords with None
        for kword in keywords:
            if kword not in fetch_args:
                fetch_args[kword] = None

        return fetch_args

    def visit_ClassDef(self, node):  # pylint: disable=C0103
        """
        Visit ClassDef on AST and save current Class.
        :param node: AST node to be evaluated
        :type node: ast.*
        """
        if node.name in self.tests:
            self.current_klass = node.name
            self.asgmts[self.current_klass] = {}
            self.generic_visit(node)

    def visit_FunctionDef(self, node):  # pylint: disable=C0103
        """
        Visit FunctionDef on AST and save current method.
        :param node: AST node to be evaluated
        :type node: ast.*
        """
        # make sure we are into a class method and not a fuction
        if self.current_klass:
            self.current_method = node.name
            self.asgmts[self.current_klass][self.current_method] = {}
        self.generic_visit(node)

    def visit_Assign(self, node):  # pylint: disable=C0103
        """
        Visit Assign on AST and build list of assignments that matches the
        pattern pattern `name = string`.
        :param node: AST node to be evaluated
        :type node: ast.*
        """
        if isinstance(node.value, ast.Str):
            # make sure we are into a class method, we are not supporting
            # attributes and module constant assignments at this time
            if self.current_klass and self.current_method:
                # variables to make dictionary assignment line shorter
                cur_klass = self.current_klass
                cur_method = self.current_method
                name = node.targets[0].id
                self.asgmts[cur_klass][cur_method][name] = node.value.s
        self.generic_visit(node)

    def visit_Call(self, node):  # pylint: disable=C0103
        """
        Visit Calls on AST and build list of calls that matches the pattern.
        :param node: AST node to be evaluated
        :type node: ast.*
        """
        # make sure we are into a class method
        if self.current_klass and self.current_method:
            if isinstance(node.func, ast.Attribute):
                if self.pattern in node.func.attr:
                    call = self._parse_args(node)
                    if call:
                        self.calls.append(call)


def fetch_assets(test_file):
    """
    Fetches the assets based on keywords listed on FetchAssetHandler.calls.
    :param test_file: File name of instrumented test to be evaluated
    :type test_file: str
    :returns: list of names that were successfuly fetched and list of
    fails.
    """
    cache_dirs = data_dir.get_cache_dirs()
    success = []
    fail = []
    handler = FetchAssetHandler(test_file)
    for call in handler.calls:
        expire = call.pop('expire', None)
        if expire is not None:
            expire = data_structures.time_to_seconds(str(expire))
        try:
            # make dictionary unpacking compatible with python 3.4 as it does
            # not support constructions like:
            # Asset(**call, cache_dirs=cache_dirs, expire=expire)
            call['cache_dirs'] = cache_dirs
            call['expire'] = expire
            asset_obj = Asset(**call)
            asset_obj.fetch()
            success.append(call['name'])
        except EnvironmentError as failed:
            fail.append(failed)
    return success, fail


class Assets(CLICmd):
    """
    Implements the avocado 'assets' subcommand
    """
    name = 'assets'
    description = 'Manage assets'

    def configure(self, parser):
        """
        Add the subparser for the assets action.

        :param parser: The Avocado command line application parser
        :type parser: :class:`avocado.core.parser.ArgumentParser`
        """
        parser = super(Assets, self).configure(parser)

        subcommands = parser.add_subparsers(dest='assets_subcommand')
        subcommands.required = True

        fetch_subcommand_parser = subcommands.add_parser(
            'fetch',
            help='Fetch assets from test source or config file if it\'s not'
            ' already in the cache')
        fetch_subcommand_parser.add_argument('references', nargs='+',
                                             metavar='TEST_REFERENCE',
                                             help='List of test references')

    def run(self, config):
        subcommand = config.get('assets_subcommand')
        # we want to let the command caller knows about fails
        exitcode = exit_codes.AVOCADO_ALL_OK

        if subcommand == 'fetch':
            # fetch assets from instrumented tests
            for test_file in config['references']:
                if os.path.isfile(test_file) and test_file.endswith('.py'):
                    LOG_UI.debug('Fetching assets from %s.', test_file)
                    success, fail = fetch_assets(test_file)

                    if not success and not fail:
                        LOG_UI.warning('No supported fetch_asset statement'
                                       ' found.')
                        exitcode |= exit_codes.AVOCADO_FAIL
                    else:
                        for asset_file in success:
                            LOG_UI.debug('  File %s fetched or already on'
                                         ' cache.', asset_file)
                        for asset_file in fail:
                            LOG_UI.error(asset_file)

                    if fail:
                        exitcode |= exit_codes.AVOCADO_FAIL
                else:
                    LOG_UI.warning('No such file or file not supported: %s',
                                   test_file)
                    exitcode |= exit_codes.AVOCADO_FAIL

        return exitcode
