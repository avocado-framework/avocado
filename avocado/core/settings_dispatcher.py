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
# Copyright: Red Hat Inc. 2018-2019

"""
Settings Dispatcher

This is a special case for the dispatchers that can be found in
:mod:`avocado.core.dispatcher`.  This one deals with settings that
will be read by the other dispatchers, while still being a dispatcher
for configuration sources.
"""

from avocado.core.extension_manager import ExtensionManager


class SettingsDispatcher(ExtensionManager):

    """
    Dispatchers that allows plugins to modify settings

    It's not the standard "avocado.core.dispatcher" because that one depends
    on settings. This dispatcher is the bare-stevedore dispatcher which is
    executed before settings is parsed.
    """

    def __init__(self):
        super(SettingsDispatcher, self).__init__('avocado.plugins.settings')
