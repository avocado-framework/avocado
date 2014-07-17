#!/usr/bin/env python

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
# Author: Cleber Rosa <cleber@redhat.com>

import unittest

from avocado import gdbmi

class ParserTest(unittest.TestCase):

    def test_parse_unknown_key(self):
        self.assertRaises(gdbmi.UnknownKeyError, gdbmi.parse_line, "<foo,bar,baz=for",)

    def test_parse_line(self):
        # FIXME: method currently returns only the statement
        self.assertEqual(gdbmi.parse_line('=thread-group-added,id="i1"'),
                         'thread-group-added')

    def test_encode_cli_command(self):
        self.assertEqual(gdbmi.encode_cli_command("file /dev/null"),
                         '-interpreter-exec console "file /dev/null"')


if __name__ == '__main__':
    unittest.main()
