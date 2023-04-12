Advanced logging capabilities
=============================

Avocado provides advanced logging capabilities at test run time.  These can
be combined with the standard Python library APIs on tests.

One common example is the need to follow specific progress on longer or more
complex tests. Let's look at a very simple test example, but one multiple
clear stages on a single test:

.. literalinclude:: ../../../../../examples/tests/logging_streams.py

Currently Avocado will store any log information that is part of the
'avocado.*' namespaces. You just need to choose a namespace when setting up
your logger. For storing logs into test log file you have to use
`avocado.test.*` namespace.

Avocado uses four main namespaces, each of them prints logs into different
locations and you can use these namespaces in your tests if you want to
adjust your logs:

:avocado: Main namespace every log has to by under this namespace to be part of avocado logs.
:avocado.app: Everything in this stream will be printed to console
:avocado.test: All logs under this namespace will be stored into {logs_dir}/test-results/{test-id}/debug.log
:avocado.job: All logs under this namespace will be stored into {logs_dir}/job.log

.. note:: Sometimes you might want to store logs, which is not part of 
   `avocado.*` name space. For that, you can use `--store-logging-stream`
   option.

The result is that, besides all the other log files commonly generated, as part
of the `debug.log` file at the job results dir, you can get your logging
information.  During the test run, one could watch the progress with::

        $ tail -f ~/avocado/job-results/latest/test-results/1-examples_tests_logging_streams.py_Plant.test_plant_organic/debug.log
        [stdlog] 2023-04-13 17:05:47,100 avocado.test INFO | INIT 1-examples/tests/logging_streams.py:Plant.test_plant_organic
        [stdlog] 2023-04-13 17:05:47,101 avocado.test DEBUG| PARAMS (key=timeout, path=*, default=None) => None
        [stdlog] 2023-04-13 17:05:47,101 avocado.test DEBUG| Test metadata:
        [stdlog] 2023-04-13 17:05:47,101 avocado.test DEBUG|   filename: /home/janrichter/Avocado/avocado/examples/tests/logging_streams.py
        [stdlog] 2023-04-13 17:05:47,101 avocado.test DEBUG|   teststmpdir: /var/tmp/avocado_zcr9t0f7
        [stdlog] 2023-04-13 17:05:47,102 avocado.test INFO | START 1-examples/tests/logging_streams.py:Plant.test_plant_organic
        [stdlog] 2023-04-13 17:05:47,102 avocado.test DEBUG| PARAMS (key=rows, path=*, default=3) => 3
        [stdlog] 2023-04-13 17:05:47,102 avocado.test.progress INFO | preparing soil on row 0
        [stdlog] 2023-04-13 17:05:47,103 avocado.test.progress INFO | preparing soil on row 1
        [stdlog] 2023-04-13 17:05:47,103 avocado.test.progress INFO | preparing soil on row 2
        [stdlog] 2023-04-13 17:05:47,103 avocado.test.progress INFO | letting soil rest before throwing seeds
        [stdlog] 2023-04-13 17:05:48,104 avocado.test.progress INFO | throwing seeds on row 0
        [stdlog] 2023-04-13 17:05:48,104 avocado.test.progress INFO | throwing seeds on row 1
        [stdlog] 2023-04-13 17:05:48,105 avocado.test.progress INFO | throwing seeds on row 2
        [stdlog] 2023-04-13 17:05:48,105 avocado.test.progress INFO | waiting for Avocados to grow
        [stdlog] 2023-04-13 17:05:50,107 avocado.test.progress INFO | harvesting organic avocados on row 0
        [stdlog] 2023-04-13 17:05:50,108 avocado.test.progress INFO | harvesting organic avocados on row 1
        [stdlog] 2023-04-13 17:05:50,108 avocado.test.progress INFO | harvesting organic avocados on row 2
        [stdlog] 2023-04-13 17:05:50,108 avocado.test.progress ERROR| Avocados are Gone
        [stdlog] 2023-04-13 17:05:50,109 avocado.test INFO | PASS 1-examples/tests/logging_streams.py:Plant.test_plant_organic
        [stdlog] 2023-04-13 17:05:50,110 avocado.test INFO |


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

        JOB ID     : e236a04a03620aa73d5ce48e779ecbfd495bf940
        JOB LOG    : /home/user/avocado/job-results/job-2023-04-19T11.50-e236a04/job.log
        (1/1) examples/tests/logging_streams.py:Plant.test_plant_organic: STARTED
        avocado.test.progress: 1-examples/tests/logging_streams.py:Plant.test_plant_organic: preparing soil on row 0
        avocado.test.progress: 1-examples/tests/logging_streams.py:Plant.test_plant_organic: preparing soil on row 1
        avocado.test.progress: 1-examples/tests/logging_streams.py:Plant.test_plant_organic: preparing soil on row 2
        avocado.test.progress: 1-examples/tests/logging_streams.py:Plant.test_plant_organic: letting soil rest before throwing seeds
        avocado.test.progress: 1-examples/tests/logging_streams.py:Plant.test_plant_organic: throwing seeds on row 0
        avocado.test.progress: 1-examples/tests/logging_streams.py:Plant.test_plant_organic: throwing seeds on row 1
        avocado.test.progress: 1-examples/tests/logging_streams.py:Plant.test_plant_organic: throwing seeds on row 2
        avocado.test.progress: 1-examples/tests/logging_streams.py:Plant.test_plant_organic: waiting for Avocados to grow
        avocado.test.progress: 1-examples/tests/logging_streams.py:Plant.test_plant_organic: harvesting organic avocados on row 0
        avocado.test.progress: 1-examples/tests/logging_streams.py:Plant.test_plant_organic: harvesting organic avocados on row 1
        avocado.test.progress: 1-examples/tests/logging_streams.py:Plant.test_plant_organic: harvesting organic avocados on row 2
        1-examples/tests/logging_streams.py:Plant.test_plant_organic: Avocados have been harvested.
        avocado.test.progress: 1-examples/tests/logging_streams.py:Plant.test_plant_organic: Avocados are Gone
        (1/1) examples/tests/logging_streams.py:Plant.test_plant_organic: PASS (3.02 s)
        RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
        JOB HTML   : /home/user/avocado/job-results/job-2023-04-19T11.50-e236a04/results.html
        JOB TIME   : 4.34 s


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
    2023-04-19 11:52:09,473 avocado.test.progress INFO | preparing soil on row 2
    2023-04-19 11:52:09,473 avocado.test.progress INFO | letting soil rest before throwing seeds
    2023-04-19 11:52:10,474 avocado.test.progress INFO | throwing seeds on row 0
    2023-04-19 11:52:10,474 avocado.test.progress INFO | throwing seeds on row 1
    2023-04-19 11:52:10,474 avocado.test.progress INFO | throwing seeds on row 2
    2023-04-19 11:52:10,475 avocado.test.progress INFO | waiting for Avocados to grow
    2023-04-19 11:52:12,476 avocado.test.progress INFO | harvesting organic avocados on row 0
    2023-04-19 11:52:12,477 avocado.test.progress INFO | harvesting organic avocados on row 1
    2023-04-19 11:52:12,478 avocado.test.progress INFO | harvesting organic avocados on row 2
    2023-04-19 11:52:12,478 avocado.test.progress ERROR| Avocados are Gone

The very same ``avocado.test.progress`` logger, could be used across multiple test methods
and across multiple test modules.  In the example given, the test name is used
to give extra context.

