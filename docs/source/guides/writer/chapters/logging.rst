Advanced logging capabilities
=============================

Avocado provides advanced logging capabilities at test run time.  These can
be combined with the standard Python library APIs on tests.

One common example is the need to follow specific progress on longer or more
complex tests. Let's look at a very simple test example, but one multiple
clear stages on a single test:

.. literalinclude:: ../../../../../examples/tests/logging_streams.py

.. note:: TODO: Improve how we show the logs on the console.

The custom ``progress`` stream is combined with the application output, which
may or may not suit your needs or preferences. If you want the ``progress``
stream to be sent to a separate file, both for clarity and for persistence,
you can run Avocado like this::

    $ avocado run --store-logging-stream=progress -- logging_streams.py

The result is that, besides all the other log files commonly generated, there
will be another log file named ``progress.INFO`` at the job results
dir. During the test run, one could watch the progress with::

    $ tail -f ~/avocado/job-results/latest/progress.INFO
    10:36:59 INFO | 1-logging_streams.py:Plant.test_plant_organic: preparing soil on row 0
    10:36:59 INFO | 1-logging_streams.py:Plant.test_plant_organic: preparing soil on row 1
    10:36:59 INFO | 1-logging_streams.py:Plant.test_plant_organic: preparing soil on row 2
    10:36:59 INFO | 1-logging_streams.py:Plant.test_plant_organic: letting soil rest before throwing seeds
    10:37:01 INFO | 1-logging_streams.py:Plant.test_plant_organic: throwing seeds on row 0
    10:37:01 INFO | 1-logging_streams.py:Plant.test_plant_organic: throwing seeds on row 1
    10:37:01 INFO | 1-logging_streams.py:Plant.test_plant_organic: throwing seeds on row 2
    10:37:01 INFO | 1-logging_streams.py:Plant.test_plant_organic: waiting for Avocados to grow
    10:37:06 INFO | 1-logging_streams.py:Plant.test_plant_organic: harvesting organic avocados on row 0
    10:37:06 INFO | 1-logging_streams.py:Plant.test_plant_organic: harvesting organic avocados on row 1
    10:37:06 INFO | 1-logging_streams.py:Plant.test_plant_organic: harvesting organic avocados on row 2

The very same ``progress`` logger, could be used across multiple test methods
and across multiple test modules.  In the example given, the test name is used
to give extra context.
