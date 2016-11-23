#!/usr/bin/env python

from avocado import main
from avocado import Test


class PassTest(Test):

    """
    Example test that passes.

    :avocado: tags=fast
    """

    def test(self):
        """
        A test simply doesn't have to fail in order to pass
        """
        pass


if __name__ == "__main__":
    main()
