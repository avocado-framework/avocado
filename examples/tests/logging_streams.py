import logging
import time

from avocado import Test


class Plant(Test):
    """Logs parts of the test progress in an specific logging stream."""

    def test_plant_organic(self):
        progress_log = logging.getLogger("avocado.test.progress")
        rows = int(self.params.get("rows", default=3))

        # Preparing soil
        for row in range(rows):
            progress_log.info("%s: preparing soil on row %s",
                              self.name, row)

        # Letting soil rest
        progress_log.info("%s: letting soil rest before throwing seeds",
                          self.name)
        time.sleep(1)

        # Throwing seeds
        for row in range(rows):
            progress_log.info("%s: throwing seeds on row %s",
                              self.name, row)

        # Let them grow
        progress_log.info("%s: waiting for Avocados to grow",
                          self.name)
        time.sleep(2)

        # Harvest them
        for row in range(rows):
            progress_log.info("%s: harvesting organic avocados on row %s",
                              self.name, row)
