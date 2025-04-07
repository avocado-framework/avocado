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
# Copyright: Red Hat Inc. 2015
# Author: Cleber Rosa <cleber@redhat.com>
"""
Plugins information plugin
"""
import itertools

from avocado.core import dispatcher
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.settings import settings
from avocado.core.spawners.common import SpawnCapabilities
from avocado.utils import astring


class Plugins(CLICmd):
    """
    Plugins information
    """

    name = "plugins"
    description = "Displays plugin information"

    def configure(self, parser):
        parser = super().configure(parser)
        help_msg = "Will list the plugins in execution order"
        settings.register_option(
            section="plugins",
            key="ordered_list",
            default=False,
            key_type=bool,
            action="store_true",
            help_msg=help_msg,
            parser=parser,
            long_arg="--ordered",
            short_arg="-o",
        )

        help_msg = "Display the spawner plugins capabilities"
        settings.register_option(
            section="plugins",
            key="capabilities",
            default=False,
            key_type=bool,
            action="store_true",
            help_msg=help_msg,
            parser=parser,
            long_arg="--capabilities",
        )

    def run(self, config):

        if config.get("plugins.capabilities"):
            spawners_dispatcher = dispatcher.SpawnerDispatcher(config, None)

            LOG_UI.info(f"{spawners_dispatcher.PLUGIN_DESCRIPTION}:")

            capabilities_matrix = []
            for spawner in spawners_dispatcher.get_extentions_by_name():
                capabilities_matrix.append((spawner.name, spawner.obj.description, ""))
                for capability in SpawnCapabilities:
                    if capability in spawner.obj.CAPABILITIES:
                        capabilities_matrix.append(("", f"{capability.value}:", "yes"))
                    else:
                        capabilities_matrix.append(("", f"{capability.value}:", "no"))
                capabilities_matrix.append(("", "", ""))
            if not capabilities_matrix:
                LOG_UI.debug("(No active spawner)")
            else:
                for line in astring.iter_tabular_output(capabilities_matrix):
                    LOG_UI.debug(line)
        else:
            for plugin_dispatcher, config_needed, job_needed in itertools.chain(
                dispatcher.get_dispatchers("avocado.core.dispatcher"),
                dispatcher.get_dispatchers("avocado.core.resolver"),
            ):
                if not config_needed:
                    plugins_active = plugin_dispatcher()
                elif config_needed and not job_needed:
                    plugins_active = plugin_dispatcher(config)
                else:
                    plugins_active = plugin_dispatcher(config, None)
                msg = f"{plugins_active.PLUGIN_DESCRIPTION}:"

                LOG_UI.info(msg)
                plugin_matrix = []
                if config.get("plugins.ordered_list"):
                    sorted_plugins = plugins_active.get_extentions_by_priority()
                else:
                    sorted_plugins = plugins_active.get_extentions_by_name()
                for plugin in sorted_plugins:
                    plugin_matrix.append((plugin.name, plugin.obj.description))

                if not plugin_matrix:
                    LOG_UI.debug("(No active plugin)")
                else:
                    for line in astring.iter_tabular_output(plugin_matrix):
                        LOG_UI.debug(line)
                LOG_UI.debug("")
