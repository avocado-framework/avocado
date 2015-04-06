#!/usr/bin/python

import base64

from avocado import test
from avocado import job


class WhiteBoard(test.Test):

    """
    Simple test that saves test custom data to the test whiteboard
    """

    def action(self):
        data_file = self.params.get('whiteboard_data_file', '')
        data_size = self.params.get('whiteboard_data_size', '10')
        if data_file:
            self.log.info('Writing data to whiteboard from file: %s',
                          data_file)
            whiteboard_file = open(data_file, 'r')
            size = int(data_size)
            data = whiteboard_file.read(size)
        else:
            offset = int(data_size) - 1
            data = self.params.get('whiteboard_data_text',
                                   'default whiteboard text')[0:offset]

        iterations = int(self.params.get('whiteboard_writes', 1))

        result = ''
        for _ in xrange(0, iterations):
            result += data
        self.whiteboard = base64.encodestring(result)

if __name__ == "__main__":
    job.main()
