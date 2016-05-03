#!/usr/bin/env python

from avocado import main
from avocado import Test


class PassTest(Test):

    """
    Example test that passes.
    """
    def __init__(self, *args, **kwargs):
        kwargs["name"] = "ugly test name"
        super(PassTest, self).__init__(*args, **kwargs)

    def test(self):
        """
        A test simply doesn't have to fail in order to pass
        """
        pass


if __name__ == "__main__":
    main()
