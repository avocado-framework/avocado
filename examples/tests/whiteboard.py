#!/usr/bin/env python3

import base64

from avocado import Test


class WhiteBoard(Test):

    """
    Example of whiteboard usage.
    """

    def test(self):
        """
        This should write a message to the whiteboard.
        """
        self.whiteboard = base64.encodebytes(b'My message encoded in base64').decode('ascii')
