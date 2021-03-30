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
# Copyright: 2016 Red Hat, Inc.
# Author: Lukas Doktor <ldoktor@redhat.com>
"""
avocado.utils.stacktrace unittests
"""

import pickle
import re
import unittest

from avocado.utils import stacktrace


class Unpickable:
    """
    Dummy class which does not support pickling
    """

    def __getstate__(self):
        raise pickle.PickleError


class InClassUnpickable:
    """
    Dummy class containing unpickable object inside itself
    """

    def __init__(self):
        self.troublemaker = Unpickable()


class ListWithUnpickableAttribute(list):
    """
    Dummy list class containing also unpickable attribute
    """

    def __init__(self, *args, **kwargs):
        self.__troublemaker = Unpickable()
        super(ListWithUnpickableAttribute, self).__init__(*args, **kwargs)


class TestUnpickableObject(unittest.TestCase):

    """
    Basic selftests for `avocado.utils.stacktrace.str_unpickable_object
    """

    def test_raises(self):
        self.assertRaises(ValueError, stacktrace.str_unpickable_object,
                          ([{"foo": set([])}]))

    def test_basic(self):
        """ Basic usage """
        def check(exps, obj):
            """ Search exps in the output of str_unpickable_object(obj) """
            act = stacktrace.str_unpickable_object(obj)
            for exp in exps:
                if not re.search(exp, act):
                    self.fail("%r no match in:\n%s" % (exp, act))
        check(["this => .*Unpickable"], Unpickable())
        check([r"this\[0\]\[0\]\[foo\]\.troublemaker => .*Unpickable"],
              [[{"foo": InClassUnpickable()}]])
        check([r"this\[foo\] => \[1, 2, 3\]"],
              {"foo": ListWithUnpickableAttribute([1, 2, 3])})
        check([r"this\[foo\]\[3\] => .*Unpickable"],
              {"foo": ListWithUnpickableAttribute([1, 2, 3, Unpickable()])})
        check([r"this\[2\] => .*Unpickable",
               r"this\[3\]\[foo\].troublemaker => .*Unpickable",
               r"this\[4\]\[0\].troublemaker => .*Unpickable"],
              [1, 2, Unpickable(), {"foo": InClassUnpickable(), "bar": None},
               ListWithUnpickableAttribute(ListWithUnpickableAttribute(
                   [InClassUnpickable()]))])


if __name__ == '__main__':
    unittest.main()
