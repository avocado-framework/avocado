#!/usr/bin/env python

from avocado import main
from avocado import Test


class SetupRetry(Test):

    """
    Example test for a setUp() method that will fail for a number of times

    :avocado: tags=fast
    """

    count = 0

    def setUp(self):
        self.count += 1
        setup_failures = int(self.params.get("setup_failures", default=2))
        if self.count <= setup_failures:
            raise RuntimeError

    def test(self):
        """
        A test simply doesn't have to fail in order to pass
        """


if __name__ == "__main__":
    main()
