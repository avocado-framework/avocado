#!/usr/bin/env python

import base64

from avocado import Test
from avocado import main


class WhiteBoard(Test):

    """
    Example of whiteboard usage.
    """

    def test(self):
        """
        This should write a message to the whiteboard.
        """
        self.whiteboard = base64.encodestring(b'My message encoded in base64').decode('ascii')


if __name__ == "__main__":
    main()
