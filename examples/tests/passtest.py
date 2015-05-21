#!/usr/bin/python

from avocado import main
from avocado import test


class PassTest(test.Test):

    """
    Example test that passes.
    """

    def runTest(self):
        """
        A test simply doesn't have to fail in order to pass
        """
        self.params.get('asdf', 'aaa/*', 1)
        self.params.set('asdf', '**', 2)
        self.params.get('asdf', 'aaa/*', 3)
        self.params.get('asdf', '/*', 4)
        pass


if __name__ == "__main__":
    main()
