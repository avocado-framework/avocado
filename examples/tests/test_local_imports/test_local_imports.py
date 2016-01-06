#!/usr/bin/env python

from avocado import main
from avocado import Test

from mylib import hello


class LocalImportTest(Test):

    """
    Functional avocado test for local imports.
    """

    def test(self):
        """
        Log a string coming from a local import.
        """
        self.log.info(hello())


if __name__ == "__main__":
    main()
