Advanced logging capabilities
=============================

Avocado provides advanced logging capabilities at test run time.  These can
be combined with the standard Python library APIs on tests.

One common example is the need to follow specific progress on longer or more
complex tests. Let's look at a very simple test example, but one multiple
clear stages on a single test:

.. literalinclude:: ../../../../../examples/tests/logging_streams.py

.. note:: TODO: Improve how we show the logs on the console.

Currently Avocado will store any log information that is part of the
'avocado.*' namespaces. You just need to choose a namespace when setting up
your logger.

The result is that, besides all the other log files commonly generated, as part
of the `debug.log` file at the job results dir, you can get your logging
information.  During the test run, one could watch the progress with::

        $ tail -f ~/avocado/job-results/latest/test-results/1-_tmp_plant.py_Plant.test_plant_organic/debug.log
        [stdlog] 2021-10-06 09:18:57,989 avocado.test.progress L0018 INFO | 1-Plant.test_plant_organic: preparing soil on row 1
        [stdlog] 2021-10-06 09:18:57,989 avocado.test.progress L0018 INFO | 1-Plant.test_plant_organic: preparing soil on row 2
        [stdlog] 2021-10-06 09:18:57,989 avocado.test.progress L0022 INFO | 1-Plant.test_plant_organic: letting soil rest before throwing seeds
        [stdlog] 2021-10-06 09:18:58,990 avocado.test.progress L0028 INFO | 1-Plant.test_plant_organic: throwing seeds on row 0
        [stdlog] 2021-10-06 09:18:58,991 avocado.test.progress L0028 INFO | 1-Plant.test_plant_organic: throwing seeds on row 1
        [stdlog] 2021-10-06 09:18:58,991 avocado.test.progress L0028 INFO | 1-Plant.test_plant_organic: throwing seeds on row 2
        [stdlog] 2021-10-06 09:18:58,992 avocado.test.progress L0032 INFO | 1-Plant.test_plant_organic: waiting for Avocados to grow
        [stdlog] 2021-10-06 09:19:00,995 avocado.test.progress L0038 INFO | 1-Plant.test_plant_organic: harvesting organic avocados on row 0
        [stdlog] 2021-10-06 09:19:00,995 avocado.test.progress L0038 INFO | 1-Plant.test_plant_organic: harvesting organic avocados on row 1
        [stdlog] 2021-10-06 09:19:00,996 avocado.test.progress L0038 INFO | 1-Plant.test_plant_organic: harvesting organic avocados on row 2


The very same namespace for the logger (``avocado.test.progress``), could be used
across multiple test methods and across multiple test modules.  In the example
given, the test name is used to give extra context.
