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

.. note:: Sometimes you might want to store logs, which is not part of 
   `avocado.*` name space. For that, you can use `--store-logging-stream`
   option.

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

Showing custom log streams
--------------------------

Using --show
~~~~~~~~~~~~

Alternatively, you can ask Avocado to show your logging stream, either
exclusively or in addition to other builtin streams::

    $ avocado --show app,avocado.test.progress run -- examples/tests/logging_streams.py

The outcome should be similar to::

    JOB ID     : af786f86db530bff26cd6a92c36e99bedcdca95b
    JOB LOG    : /home/user/avocado/job-results/job-2016-03-18T10.29-af786f8/job.log
    (1/1) examples/tests/logging_streams.py:Plant.test_plant_organic: STARTED
    1-examples/tests/logging_streams.py:Plant.test_plant_organic: avocado.test.progress: 1-Plant.test_plant_organic: preparing soil on row 0
    1-examples/tests/logging_streams.py:Plant.test_plant_organic: avocado.test.progress: 1-Plant.test_plant_organic: preparing soil on row 1
    1-examples/tests/logging_streams.py:Plant.test_plant_organic: avocado.test.progress: 1-Plant.test_plant_organic: preparing soil on row 2
    1-examples/tests/logging_streams.py:Plant.test_plant_organic: avocado.test.progress: 1-Plant.test_plant_organic: letting soil rest before throwing seeds
    1-examples/tests/logging_streams.py:Plant.test_plant_organic: avocado.test.progress: 1-Plant.test_plant_organic: throwing seeds on row 0
    1-examples/tests/logging_streams.py:Plant.test_plant_organic: avocado.test.progress: 1-Plant.test_plant_organic: throwing seeds on row 1
    1-examples/tests/logging_streams.py:Plant.test_plant_organic: avocado.test.progress: 1-Plant.test_plant_organic: throwing seeds on row 2
    1-examples/tests/logging_streams.py:Plant.test_plant_organic: avocado.test.progress: 1-Plant.test_plant_organic: waiting for Avocados to grow
    1-examples/tests/logging_streams.py:Plant.test_plant_organic: avocado.test.progress: 1-Plant.test_plant_organic: harvesting organic avocados on row 0
    1-examples/tests/logging_streams.py:Plant.test_plant_organic: avocado.test.progress: 1-Plant.test_plant_organic: harvesting organic avocados on row 1
    1-examples/tests/logging_streams.py:Plant.test_plant_organic: avocado.test.progress: 1-Plant.test_plant_organic: harvesting organic avocados on row 2
     (1/1) examples/tests/logging_streams.py:Plant.test_plant_organic: PASS (3.02 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB TIME   : 7.11 s
    JOB HTML   : /home/user/avocado/job-results/job-2016-03-18T10.29-af786f8/html/results.html


Using --store-logging-stream
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The custom ``avocado.test.progress`` stream is combined with the application output, which
may or may not suit your needs or preferences. If you want the ``avocado.test.progress``
stream to be sent to a separate file, both for clarity and for persistence,
you can run Avocado like this::

     $ avocado run --store-logging-stream=avocado.test.progress -- examples/tests/logging_streams.py

The result is that, besides all the other log files commonly generated, there
will be another log file named ``avocado.test.progress`` at the test results
dir. During the test run, one could watch the progress with::

    $ tail -f ~/avocado/job-results/latest/test-results/1-examples_tests_logging_streams.py_Plant.test_plant_organic/avocado.test.progress 
    2021-11-02 11:42:19,148 logging_streams  L0016 INFO | 1-Plant.test_plant_organic: preparing soil on row 1
    2021-11-02 11:42:19,148 logging_streams  L0016 INFO | 1-Plant.test_plant_organic: preparing soil on row 2
    2021-11-02 11:42:19,148 logging_streams  L0020 INFO | 1-Plant.test_plant_organic: letting soil rest before throwing seeds
    2021-11-02 11:42:20,149 logging_streams  L0026 INFO | 1-Plant.test_plant_organic: throwing seeds on row 0
    2021-11-02 11:42:20,149 logging_streams  L0026 INFO | 1-Plant.test_plant_organic: throwing seeds on row 1
    2021-11-02 11:42:20,149 logging_streams  L0026 INFO | 1-Plant.test_plant_organic: throwing seeds on row 2
    2021-11-02 11:42:20,149 logging_streams  L0030 INFO | 1-Plant.test_plant_organic: waiting for Avocados to grow
    2021-11-02 11:42:22,151 logging_streams  L0036 INFO | 1-Plant.test_plant_organic: harvesting organic avocados on row 0
    2021-11-02 11:42:22,152 logging_streams  L0036 INFO | 1-Plant.test_plant_organic: harvesting organic avocados on row 1
    2021-11-02 11:42:22,152 logging_streams  L0036 INFO | 1-Plant.test_plant_organic: harvesting organic avocados on row 2

The very same ``avocado.test.progress`` logger, could be used across multiple test methods
and across multiple test modules.  In the example given, the test name is used
to give extra context.

