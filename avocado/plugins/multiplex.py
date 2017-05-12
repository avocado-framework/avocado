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

from avocado.core.output import LOG_UI

from .variants import Variants


class Multiplex(Variants):

    """
    DEPRECATED version of the "avocado multiplex" command which is replaced
    by "avocado variants" one.
    """

    name = "multiplex"

    def run(self, args):
        LOG_UI.warning("The 'avocado multiplex' command is deprecated by the "
                       "'avocado variants' one. Please start using that one "
                       "instead as this will be removed in Avocado 52.0.")
        super(Multiplex, self).run(args)
