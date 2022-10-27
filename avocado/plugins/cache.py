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
# Copyright: Red Hat Inc. 2022
# Author: Jan Richter <jarichte@redhat.com>

from avocado.core.dispatcher import CacheDispatcher
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.settings import settings


class Cache(CLICmd):

    """
    Implements the avocado 'cache' subcommand
    """

    name = "cache"
    description = "Interface for manipulating the Avocado cache metadata"

    def _list_plugin_entries(self, plugins, selected_plugins):
        if not selected_plugins:
            selected_plugins = [p.name for p in plugins]
        for plugin in plugins:
            if plugin.name in selected_plugins:
                LOG_UI.debug("%s:", plugin.obj.name)
                cache_list = "\t" + "\t".join(plugin.obj.list().splitlines(True))
                LOG_UI.debug("%s\n", cache_list)

    def _clear_plugin_entries(self, plugins, selected_plugins):
        if not selected_plugins:
            selected_plugins = [p.name for p in plugins]
        for plugin in plugins:
            if plugin.name in selected_plugins:
                plugin.obj.clear()

    def configure(self, parser):
        """
        Add the subparser for the cache action.

        :param parser: The Avocado command line application parser
        :type parser: :class:`avocado.core.parser.ArgumentParser`
        """
        parser = super().configure(parser)
        subcommands = parser.add_subparsers(dest="cache_subcommand")
        subcommands.required = True
        list_help_msg = "List metadata in avocado cache"
        list_parser = subcommands.add_parser("list", help=list_help_msg)
        settings.register_option(
            section="cache",
            key="list",
            key_type=list,
            default=[],
            help_msg=list_help_msg,
        )

        settings.add_argparser_to_option(
            namespace="cache.list",
            nargs="*",
            metavar="CACHE_TYPE",
            parser=list_parser,
            long_arg=None,
            positional_arg=True,
            allow_multiple=True,
        )

        clear_help_msg = (
            "Clear avocado cache, you can specify which part of cache"
            " will be removed."
        )
        clear_parser = subcommands.add_parser("clear", help=clear_help_msg)
        settings.register_option(
            section="cache",
            key="clear",
            key_type=list,
            default=[],
            help_msg=clear_help_msg,
        )

        settings.add_argparser_to_option(
            namespace="cache.clear",
            nargs="*",
            metavar="CACHE_TYPE",
            parser=clear_parser,
            long_arg=None,
            positional_arg=True,
            allow_multiple=True,
        )

    def run(self, config):
        dispatcher = CacheDispatcher()
        plugins = dispatcher.get_extentions_by_priority()
        subcommand = config.get("cache_subcommand")
        if subcommand == "list":
            self._list_plugin_entries(plugins, config.get("cache.list"))
        if subcommand == "clear":
            self._clear_plugin_entries(plugins, config.get("cache.clear"))
