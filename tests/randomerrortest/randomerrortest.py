#!/usr/bin/python

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
# Copyright: Red Hat Inc. 2014
# Author: Ruda Moura <rmoura@redhat.com>


import random

from avocado import test
from avocado import job
from avocado.core import exceptions


class randomerrortest(test.Test):

    """
    Functional test for avocado. Random error test.
    """

    def action(self):
        """
        Raises a random test error.

        This test raises a random test error from
        :class:`avocado.core.exceptions`.
        """
        names = [getattr(exceptions, x) for x in dir(exceptions)]
        classes = [cls for cls in names if isinstance(cls, type)]
        classes = [cls for cls in classes if issubclass(cls, exceptions.TestBaseException)]
        cls = random.choice(classes)
        raise cls('This is a random test error!')


if __name__ == "__main__":
    job.main()
