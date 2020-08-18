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


__all__ = ['Test',
           'VERSION',
           'fail_on',
           'cancel_on',
           'skip',
           'skipIf',
           'skipUnless',
           'TestError',
           'TestFail',
           'TestCancel']


from avocado.core import register_core_options, initialize_plugins
from avocado.core.settings import settings

register_core_options()
settings.merge_with_configs()
initialize_plugins()
settings.merge_with_configs()

from avocado.core.decorators import (cancel_on, fail_on, skip, skipIf,
                                     skipUnless)
from avocado.core.exceptions import TestCancel, TestError, TestFail
from avocado.core.test import Test
from avocado.core.version import VERSION
