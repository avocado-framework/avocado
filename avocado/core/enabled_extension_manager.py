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
# Copyright: Red Hat Inc. 2015-2019
# Author: Cleber Rosa <cleber@redhat.com>

"""
Extension manager with disable/ordering support
"""

from avocado.core.extension_manager import ExtensionManager
from avocado.core.settings import settings


class EnabledExtensionManager(ExtensionManager):

    def __init__(self, namespace, invoke_kwds=None):
        super().__init__(namespace, invoke_kwds)
        namespace = f"{self.settings_section()}.order"
        configured_order = settings.as_dict().get(namespace)
        ordered = []
        if configured_order:
            for name in configured_order:
                for ext in self.extensions:
                    if name == ext.name:
                        ordered.append(ext)
            for ext in self.extensions:
                if ext not in ordered:
                    ordered.append(ext)
            self.extensions = ordered

    def enabled(self, extension):
        """
        Checks configuration for explicit mention of plugin in a disable list

        If configuration section or key doesn't exist, it means no plugin
        is disabled.
        """
        disabled = settings.as_dict().get('plugins.disable')
        return self.fully_qualified_name(extension) not in disabled
