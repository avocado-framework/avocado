#!/usr/bin/env python

from avocado import Test
from avocado import main

from avocado.utils.asset import find_file


class CancelByAsset(Test):

    """
    Example test that cancels the current test when an asset is not available.
    """

    def setUp(self):
        mirrors = ['https://mirrors.peers.community/mirrors/gnu/hello/',
                   'https://mirrors.kernel.org/gnu/hello/',
                   'http://gnu.c3sl.ufpr.br/ftp/',
                   'ftp://ftp.funet.fi/pub/gnu/prep/hello/']
        # Mess up with the original file name
        hello = 'HELLO-2.9.tar.gz'
        hello_locations = ["%s/%s" % (loc, hello) for loc in mirrors]

        asset_file = find_file(
            hello,
            self.cache_dirs,
            locations=hello_locations)

        if asset_file is None:
            self.cancel("Missing Asset")

    def test_wont_be_executed(self):
        """
        This won't get to be executed, given that setUp calls .cancel().
        """


if __name__ == "__main__":
    main()
