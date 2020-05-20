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


from avocado.core.test import Test
from avocado.core.version import VERSION
from avocado.core.decorators import fail_on
from avocado.core.decorators import cancel_on
from avocado.core.decorators import skip
from avocado.core.decorators import skipIf
from avocado.core.decorators import skipUnless
from avocado.core.exceptions import TestError
from avocado.core.exceptions import TestFail
from avocado.core.exceptions import TestCancel
