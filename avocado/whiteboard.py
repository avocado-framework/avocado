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
# Authors: Cleber Rosa <cleber@redhat.com>


class WhiteBoard(file):

    '''
    File-like, custom storage area for a running test.

    It will be automatically persisted by the test framework right after the
    test ends, whathever its outcome is.
    '''

    def __init__(self, test, name='whiteboard'):
        '''
        :param test: the test that owns this whiteboard instance.
        :param name: the output file name
        '''
        super(WhiteBoard, self).__init__(name, 'w', 0)
        self.test = test

    def write(self, data, log=False):
        '''
        Write data into the whiteboard

        Optionally, this can write the test data into the log so that data
        which happens to be both human readable and machine useful can be
        written at once.

        :param data: any kind of test custom data
        :param log: whether to log the written data using the test logger
        '''
        if log:
            self.test.log.debug('Whiteboard data written: %s', data)
        super(WhiteBoard, self).write(data)
