import logging
import time

from avocado import Test


class Plant(Test):
    """Logs parts of the test progress in an specific logging stream."""

    def test_plant_organic(self):
        progress_log = logging.getLogger("avocado.test.progress")
        job_log = logging.getLogger("avocado.job")
        rows = int(self.params.get("rows", default=3))

        # Preparing soil
        for row in range(rows):
            progress_log.info("preparing soil on row %s", row)
        job_log.info("Soil has been prepared.")

        # Letting soil rest
        progress_log.info("letting soil rest before throwing seeds")
        time.sleep(1)

        # Throwing seeds
        for row in range(rows):
            progress_log.info("throwing seeds on row %s", row)

        job_log.info("Seeds have been palanted.")
        # Let them grow
        progress_log.info("waiting for Avocados to grow")
        time.sleep(2)

        # Harvest them
        for row in range(rows):
            progress_log.info("harvesting organic avocados on row %s", row)

        progress_log.error("Avocados are Gone")
