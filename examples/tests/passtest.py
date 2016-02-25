#!/usr/bin/env python

from avocado import main
from avocado import Test


class PassTest(Test):

    """
    Example test that passes.
    """

    def test(self):
        """
        A test simply doesn't have to fail in order to pass
        """
        self.avocado.barrier(self.params.get("barrier", default="foo"), 2, 3600)
        pass


if __name__ == "__main__":
    main()
