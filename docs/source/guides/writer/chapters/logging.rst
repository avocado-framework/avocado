Advanced logging capabilities
=============================

Avocado provides advanced logging capabilities at test run time.  These can
be combined with the standard Python library APIs on tests.

One common example is the need to follow specific progress on longer or more
complex tests. Let's look at a very simple test example, but one multiple
clear stages on a single test::

    import logging
    import time

    from avocado import Test

    progress_log = logging.getLogger("progress")

    class Plant(Test):

        def test_plant_organic(self):
            rows = int(self.params.get("rows", default=3))

            # Preparing soil
            for row in range(rows):
                progress_log.info("%s: preparing soil on row %s",
                                  self.name, row)

            # Letting soil rest
            progress_log.info("%s: letting soil rest before throwing seeds",
                              self.name)
            time.sleep(2)

            # Throwing seeds
            for row in range(rows):
                progress_log.info("%s: throwing seeds on row %s",
                                  self.name, row)

            # Let them grow
            progress_log.info("%s: waiting for Avocados to grow",
                              self.name)
            time.sleep(5)

            # Harvest them
            for row in range(rows):
                progress_log.info("%s: harvesting organic avocados on row %s",
                                  self.name, row)


From this point on, you can ask Avocado to show your logging stream, either
exclusively or in addition to other builtin streams::

    $ avocado --show app,progress run plant.py

The outcome should be similar to::

    JOB ID     : af786f86db530bff26cd6a92c36e99bedcdca95b
    JOB LOG    : /home/cleber/avocado/job-results/job-2016-03-18T10.29-af786f8/job.log
     (1/1) plant.py:Plant.test_plant_organic: progress: 1-plant.py:Plant.test_plant_organic: preparing soil on row 0
    progress: 1-plant.py:Plant.test_plant_organic: preparing soil on row 1
    progress: 1-plant.py:Plant.test_plant_organic: preparing soil on row 2
    progress: 1-plant.py:Plant.test_plant_organic: letting soil rest before throwing seeds
    -progress: 1-plant.py:Plant.test_plant_organic: throwing seeds on row 0
    progress: 1-plant.py:Plant.test_plant_organic: throwing seeds on row 1
    progress: 1-plant.py:Plant.test_plant_organic: throwing seeds on row 2
    progress: 1-plant.py:Plant.test_plant_organic: waiting for Avocados to grow
    \progress: 1-plant.py:Plant.test_plant_organic: harvesting organic avocados on row 0
    progress: 1-plant.py:Plant.test_plant_organic: harvesting organic avocados on row 1
    progress: 1-plant.py:Plant.test_plant_organic: harvesting organic avocados on row 2
    PASS (7.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB TIME   : 7.11 s
    JOB HTML   : /home/cleber/avocado/job-results/job-2016-03-18T10.29-af786f8/html/results.html

The custom ``progress`` stream is combined with the application output, which
may or may not suit your needs or preferences. If you want the ``progress``
stream to be sent to a separate file, both for clarity and for persistence,
you can run Avocado like this::

    $ avocado run plant.py --store-logging-stream progress

The result is that, besides all the other log files commonly generated, there
will be another log file named ``progress.INFO`` at the job results
dir. During the test run, one could watch the progress with::

    $ tail -f ~/avocado/job-results/latest/progress.INFO
    10:36:59 INFO | 1-plant.py:Plant.test_plant_organic: preparing soil on row 0
    10:36:59 INFO | 1-plant.py:Plant.test_plant_organic: preparing soil on row 1
    10:36:59 INFO | 1-plant.py:Plant.test_plant_organic: preparing soil on row 2
    10:36:59 INFO | 1-plant.py:Plant.test_plant_organic: letting soil rest before throwing seeds
    10:37:01 INFO | 1-plant.py:Plant.test_plant_organic: throwing seeds on row 0
    10:37:01 INFO | 1-plant.py:Plant.test_plant_organic: throwing seeds on row 1
    10:37:01 INFO | 1-plant.py:Plant.test_plant_organic: throwing seeds on row 2
    10:37:01 INFO | 1-plant.py:Plant.test_plant_organic: waiting for Avocados to grow
    10:37:06 INFO | 1-plant.py:Plant.test_plant_organic: harvesting organic avocados on row 0
    10:37:06 INFO | 1-plant.py:Plant.test_plant_organic: harvesting organic avocados on row 1
    10:37:06 INFO | 1-plant.py:Plant.test_plant_organic: harvesting organic avocados on row 2

The very same ``progress`` logger, could be used across multiple test methods
and across multiple test modules.  In the example given, the test name is used
to give extra context.
