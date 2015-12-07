#!/usr/bin/env python

import avocado


class SkipOutsideSetup(avocado.Test):

    """
    Test illustrating the behavior of calling skip() outside setUp().
    """

    def test(self):
        """
        This should end with ERROR.

        The method skip() can only be called from inside setUp(). If called
        outside of that method, the test status will be marked as ERROR, with
        a reason message that asks you to fix your test.
        """
        self.skip('Calling skip() outside setUp() will result in ERROR')

if __name__ == "__main__":
    avocado.main()
