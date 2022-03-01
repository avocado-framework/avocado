import os
import time

from avocado import Test


class SleepTenMin(Test):

    """
    Sleeps for 10 minutes

    :avocado: tags=slow

    :param sleep_cycles: How many iterations should be executed
    :param sleep_length: single sleep duration
    :param sleep_method: what method of sleep should be used (builtin|shell)
    """

    def test(self):
        """
        Sleep for length seconds.
        """
        cycles = int(self.params.get('sleep_cycles', default=1))
        length = int(self.params.get('sleep_length', default=600))
        method = self.params.get('sleep_method', default='builtin')

        for _ in range(0, cycles):
            self.log.debug("Sleeping for %.2f seconds", length)
            if method == 'builtin':
                time.sleep(length)
            elif method == 'shell':
                os.system(f"sleep {length}")
