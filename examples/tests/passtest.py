#!/usr/bin/python

import avocado


class PassTest(avocado.Test):

    """
    Example test that passes.
    """

    def action(self):
        """
        A test simply doesn't have to fail in order to pass
        """
        pass


if __name__ == "__main__":
    avocado.main()
