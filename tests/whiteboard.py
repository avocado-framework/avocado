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
# Author: Cleber Rosa <cleber@redhat.com>

from avocado import test
from avocado import job

import base64


class whiteboard(test.Test):

    """
    Simple test that saves test custom data to the test whiteboard
    """
    default_params = {'whiteboard_data_text': 'default whiteboard text',
                      'whiteboard_data_file': '',
                      'whiteboard_data_size': '10',
                      'whiteboard_writes': '1'}

    def action(self):
        if self.params.whiteboard_data_file:
            self.log.info('Writing data to whiteboard from file: %s',
                          self.params.whiteboard_data_file)
            whiteboard_file = open(self.params.whiteboard_data_file, 'r')
            size = int(self.params.whiteboard_data_size)
            data = whiteboard_file.read(size)
        else:
            offset = int(self.params.whiteboard_data_size) - 1
            data = self.params.whiteboard_data_text[0:offset]

        iterations = int(self.params.whiteboard_writes)

        result = ''
        for i in xrange(0, iterations):
            result += data
        self.whiteboard = base64.encodestring(result)

if __name__ == "__main__":
    job.main()
