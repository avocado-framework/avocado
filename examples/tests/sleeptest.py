#!/usr/bin/python

import time

import avocado


class SleepTest(avocado.Test):

    """
    Example test for avocado.
    """
    default_params = {'sleep_length': 1.0}

    def action(self):
        """
        Sleep for length seconds.
        """
        self.log.debug("Sleeping for %.2f seconds", self.params.sleep_length)
        time.sleep(self.params.sleep_length)


if __name__ == "__main__":
    avocado.main()
