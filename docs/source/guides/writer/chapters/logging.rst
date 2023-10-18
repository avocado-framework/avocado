.. _advanced-logging:

Advanced logging capabilities
=============================

Avocado provides advanced logging capabilities at test run time.  These can
be combined with the standard Python library APIs on tests.

One common example is the need to follow specific progress on longer or more
complex tests. Let's look at a very simple test example, but one multiple
clear stages on a single test:

.. literalinclude:: ../../../../../examples/tests/logging_streams.py

Currently Avocado will store any log information that has been generated
during job run into specific log files based on used logging namespace
and process where the logs have been generated.

Avocado generate three types of log each of them with different purpose:

**1. job.log**

The `job.log` file is generated for each avocado job and it is stored directly
in `log_dir` directory. This file contains only logs from `avocado.job`
namespace and holds information about job configuration and test statuses
which were run inside the job.
The format of logs is::

        <date> <time> avocado.job <log level> | <log>

**2. full.log**

The `full.log` file is generated for each avocado job and it is stored directly
in `log_dir` directory. This file contains all logs which were generated during
job run. It is very verbose, and it contains even avocado internal logs.
If the parallel run is enabled (default behavior) the logs are not sorted and
logs from multiple tests might be mixed together. Therefore, some
post-processing of this file might be needed for full understanding of these logs.
The format of logs is::

        <date> <time> <namespace> <log level> | <testname>: <log>

**3. debug.log**

The `debug.log` file is generated for every test in avocado job and it is stored
in {logs_dir}/test-results/{test-id} directory. This file contains all logs which
were generated during one test run. (each test has its own `debug.log` file).
This file is most important for debugging one specific test.
The format of logs is::

        <stream> <date> <time> <namespace> <log level> | <log>

.. note:: Avocado uses four main namespaces, each of them prints logs into different
        locations and you can use these namespaces in your tests if you want to
        adjust your logs:

:avocado: Main namespace for avocado logs.
:avocado.test: All logs under this namespace will be stored into {logs_dir}/test-results/{test-id}/debug.log
:avocado.job: All logs under this namespace will be stored into {logs_dir}/job.log

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

     $ avocado run --store-logging-stream=avocado.test.progress -- examples/tests/logging_streams.py examples/tests/logging_streams.py

The result is that, besides all the other log files commonly generated, there
will be created two log files named ``avocado.test.progress.log`` at the test results
directory and in job log directory. In the test result directory the stream will be separated by test,
but in the job log directory the logs will be combined from all tests.

During the test run, one could watch the progress with::

    $ tail -f ~/avocado/job-results/latest/test-results/1-examples_tests_logging_streams.py_Plant.test_plant_organic/avocado.test.progress.log
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

Or to see progress from all tests::

    $ tail -f ~/avocado/job-results/latest/avocado.test.progress.log
    2023-04-13 17:49:08,687 avocado.test.progress INFO | 1-examples/tests/logging_streams.py:Plant.test_plant_organic: preparing soil on row 0
    2023-04-13 17:49:08,688 avocado.test.progress INFO | 1-examples/tests/logging_streams.py:Plant.test_plant_organic: preparing soil on row 1
    2023-04-13 17:49:08,689 avocado.test.progress INFO | 2-examples/tests/logging_streams.py:Plant.test_plant_organic: preparing soil on row 0
    2023-04-13 17:49:08,690 avocado.test.progress INFO | 2-examples/tests/logging_streams.py:Plant.test_plant_organic: preparing soil on row 1
    2023-04-13 17:49:08,740 avocado.test.progress INFO | 1-examples/tests/logging_streams.py:Plant.test_plant_organic: preparing soil on row 2
    2023-04-13 17:49:08,741 avocado.test.progress INFO | 1-examples/tests/logging_streams.py:Plant.test_plant_organic: letting soil rest before throwing seeds
    2023-04-13 17:49:08,741 avocado.test.progress INFO | 2-examples/tests/logging_streams.py:Plant.test_plant_organic: preparing soil on row 2
    2023-04-13 17:49:08,741 avocado.test.progress INFO | 2-examples/tests/logging_streams.py:Plant.test_plant_organic: letting soil rest before throwing seeds
    2023-04-13 17:49:09,599 avocado.test.progress INFO | 1-examples/tests/logging_streams.py:Plant.test_plant_organic: throwing seeds on row 0
    2023-04-13 17:49:09,600 avocado.test.progress INFO | 2-examples/tests/logging_streams.py:Plant.test_plant_organic: throwing seeds on row 0
    2023-04-13 17:49:09,651 avocado.test.progress INFO | 1-examples/tests/logging_streams.py:Plant.test_plant_organic: throwing seeds on row 1
    2023-04-13 17:49:09,651 avocado.test.progress INFO | 1-examples/tests/logging_streams.py:Plant.test_plant_organic: throwing seeds on row 2
    2023-04-13 17:49:09,651 avocado.test.progress INFO | 1-examples/tests/logging_streams.py:Plant.test_plant_organic: waiting for Avocados to grow
    2023-04-13 17:49:09,652 avocado.test.progress INFO | 2-examples/tests/logging_streams.py:Plant.test_plant_organic: throwing seeds on row 1
    2023-04-13 17:49:09,652 avocado.test.progress INFO | 2-examples/tests/logging_streams.py:Plant.test_plant_organic: throwing seeds on row 2
    2023-04-13 17:49:09,652 avocado.test.progress INFO | 2-examples/tests/logging_streams.py:Plant.test_plant_organic: waiting for Avocados to grow
    2023-04-13 17:49:11,619 avocado.test.progress INFO | 1-examples/tests/logging_streams.py:Plant.test_plant_organic: harvesting organic avocados on row 0
    2023-04-13 17:49:11,620 avocado.test.progress INFO | 1-examples/tests/logging_streams.py:Plant.test_plant_organic: harvesting organic avocados on row 1
    2023-04-13 17:49:11,621 avocado.test.progress INFO | 2-examples/tests/logging_streams.py:Plant.test_plant_organic: harvesting organic avocados on row 0
    2023-04-13 17:49:11,621 avocado.test.progress INFO | 2-examples/tests/logging_streams.py:Plant.test_plant_organic: harvesting organic avocados on row 1
    2023-04-13 17:49:11,674 avocado.test.progress INFO | 1-examples/tests/logging_streams.py:Plant.test_plant_organic: harvesting organic avocados on row 2
    2023-04-13 17:49:11,674 avocado.test.progress ERROR| 1-examples/tests/logging_streams.py:Plant.test_plant_organic: Avocados are Gone
    2023-04-13 17:49:11,675 avocado.test.progress INFO | 2-examples/tests/logging_streams.py:Plant.test_plant_organic: harvesting organic avocados on row 2
    2023-04-13 17:49:11,676 avocado.test.progress ERROR| 2-examples/tests/logging_streams.py:Plant.test_plant_organic: Avocados are Gone

The very same ``avocado.test.progress`` logger, could be used across multiple test methods
and across multiple test modules.

By default avocado is creating ``full.log`` file in job_log directory with
all avocado logs which were created during the job run::

     $ avocado run examples/tests/logging_streams.py

Again you could watch the progress with::

    $ tail -f ~/avocado/job-results/latest/test-results/full.log
    2023-04-13 17:54:18,814 avocado.app INFO | JOB ID     : 14f66b17f7c79ba6765e4d0c6a7e77b8f7fa7308
    2023-04-13 17:54:18,814 avocado.app INFO | JOB LOG    : /home/janrichter/avocado/job-results/job-2023-04-13T17.54-14f66b1/job.log
    2023-04-13 17:54:18,814 avocado.sysinfo INFO | Commands configured by file: /home/janrichter/Avocado/avocado/avocado/etc/avocado/sysinfo/commands
    2023-04-13 17:54:18,814 avocado.sysinfo INFO | Files configured by file: /home/janrichter/Avocado/avocado/avocado/etc/avocado/sysinfo/files
    2023-04-13 17:54:18,814 avocado.sysinfo DEBUG| File /home/janrichter/Avocado/avocado/avocado/etc/avocado/sysinfo/fail_commands does not exist.
    2023-04-13 17:54:18,814 avocado.sysinfo DEBUG| File /home/janrichter/Avocado/avocado/avocado/etc/avocado/sysinfo/fail_files does not exist.
    2023-04-13 17:54:18,815 avocado.sysinfo INFO | Profilers configured by file: /home/janrichter/Avocado/avocado/avocado/etc/avocado/sysinfo/profilers
    2023-04-13 17:54:18,815 avocado.sysinfo INFO | Profiler disabled
    2023-04-13 17:54:18,875 avocado.sysinfo DEBUG| Not logging /proc/slabinfo (lack of permissions)
    2023-04-13 17:54:18,901 avocado.sysinfo DEBUG| Not logging /sys/kernel/debug/sched_features (file not found)
    2023-04-13 17:54:18,901 avocado.sysinfo DEBUG| Not logging /proc/pci (file not found)
    2023-04-13 17:54:18,911 avocado.job INFO | Command line: /home/janrichter/.pyenv/versions/avocado/bin/avocado run --store-logging-stream=all -- examples/tests/logging_streams.py
    2023-04-13 17:54:18,912 avocado.job INFO |
    2023-04-13 17:54:18,914 avocado.job INFO | Avocado version: 101.0 (GIT commit bf7704ba)
    2023-04-13 17:54:18,914 avocado.job INFO |
    2023-04-13 17:54:18,914 avocado.job INFO | Avocado config:
    2023-04-13 17:54:18,914 avocado.job INFO |
    2023-04-13 17:54:18,915 avocado.job INFO | {'assets.fetch.ignore_errors': False,
    2023-04-13 17:54:18,915 avocado.job INFO |  'assets.fetch.references': [],
    2023-04-13 17:54:18,916 avocado.job INFO |  'assets.fetch.timeout': 300,
    2023-04-13 17:54:18,916 avocado.job INFO |  'assets.list.days': None,
    2023-04-13 17:54:18,916 avocado.job INFO |  'assets.list.overall_limit': None,
    2023-04-13 17:54:18,916 avocado.job INFO |  'assets.list.size_filter': None,
    2023-04-13 17:54:18,916 avocado.job INFO |  'assets.purge.days': None,
    2023-04-13 17:54:18,916 avocado.job INFO |  'assets.purge.overall_limit': None,
    2023-04-13 17:54:18,916 avocado.job INFO |  'assets.purge.size_filter': None,
    2023-04-13 17:54:18,916 avocado.job INFO |  'assets.register.name': None,
    2023-04-13 17:54:18,916 avocado.job INFO |  'assets.register.sha1_hash': None,
    2023-04-13 17:54:18,916 avocado.job INFO |  'assets.register.url': None,
    2023-04-13 17:54:18,916 avocado.job INFO |  'cache.clear': [],
    2023-04-13 17:54:18,916 avocado.job INFO |  'cache.list': [],
    2023-04-13 17:54:18,916 avocado.job INFO |  'config': None,
    2023-04-13 17:54:18,916 avocado.job INFO |  'config.datadir': False,
    2023-04-13 17:54:18,916 avocado.job INFO |  'core.paginator': False,
    2023-04-13 17:54:18,916 avocado.job INFO |  'core.show': {'app'},
    ...

External logs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your tests use some external logs which are not part of `avocado.*` namespace, avocado
will still log these logs into the standard log files.  Let's see an example with
Matplotlib external library:

.. literalinclude:: ../../../../../examples/tests/external_logging_stream.py

Avocado will add Matplotlib logs into the standard avocado logs::

     $ avocado run examples/tests/external_logging_stream.py

You can check the logs by::

        $ cat ~/avocado/job-results/latest/test-results/1-examples_tests_external_logging_stream.py_MatplotlibTest.test/debug.log
        [stdlog] 2023-04-20 10:07:03,743 matplotlib DEBUG| matplotlib data path: /home/janrichter/.pyenv/versions/avocado/lib/python3.10/site-packages/matplotlib/mpl-data
        [stdlog] 2023-04-20 10:07:03,748 matplotlib DEBUG| CONFIGDIR=/home/janrichter/.config/matplotlib
        [stdlog] 2023-04-20 10:07:03,749 matplotlib DEBUG| interactive is False
        [stdlog] 2023-04-20 10:07:03,749 matplotlib DEBUG| platform is linux
        [stdlog] 2023-04-20 10:07:03,801 matplotlib DEBUG| CACHEDIR=/home/janrichter/.cache/matplotlib
        [stdlog] 2023-04-20 10:07:03,802 matplotlib.font_manager DEBUG| Using fontManager instance from /home/janrichter/.cache/matplotlib/fontlist-v330.json
        [stdlog] 2023-04-20 10:07:03,985 avocado.test INFO | INIT 1-examples/tests/external_logging_stream.py:MatplotlibTest.test
        [stdlog] 2023-04-20 10:07:03,986 avocado.test DEBUG| PARAMS (key=timeout, path=*, default=None) => None
        [stdlog] 2023-04-20 10:07:03,986 avocado.test DEBUG| Test metadata:
        [stdlog] 2023-04-20 10:07:03,986 avocado.test DEBUG|   filename: /home/janrichter/Avocado/avocado/examples/tests/external_logging_stream.py
        [stdlog] 2023-04-20 10:07:03,986 avocado.test DEBUG|   teststmpdir: /var/tmp/avocado_3b1c_sqy
        [stdlog] 2023-04-20 10:07:03,987 avocado.test INFO | START 1-examples/tests/external_logging_stream.py:MatplotlibTest.test
        [stdlog] 2023-04-20 10:07:03,995 matplotlib.pyplot DEBUG| Loaded backend agg version v2.2.
        [stdlog] 2023-04-20 10:07:03,997 matplotlib.font_manager DEBUG| findfont: Matching sans\-serif:style=normal:variant=normal:weight=normal:stretch=normal:size=10.0.
        [stdlog] 2023-04-20 10:07:03,997 matplotlib.font_manager DEBUG| findfont: score(FontEntry(fname='/home/janrichter/.pyenv/versions/avocado/lib/python3.10/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans-Bold.ttf', name='DejaVu Sans', style='normal', variant='normal', weight=700, stretch='normal', size='scalable')) = 0.33499999999999996
        [stdlog] 2023-04-20 10:07:03,997 matplotlib.font_manager DEBUG| findfont: score(FontEntry(fname='/home/janrichter/.pyenv/versions/avocado/lib/python3.10/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSansMono-BoldOblique.ttf', name='DejaVu Sans Mono', style='oblique', variant='normal', weight=700, stretch='normal', size='scalable')) = 11.335
        [stdlog] 2023-04-20 10:07:03,997 matplotlib.font_manager DEBUG| findfont: score(FontEntry(fname='/home/janrichter/.pyenv/versions/avocado/lib/python3.10/site-packages/matplotlib/mpl-data/fonts/ttf/cmsy10.ttf', name='cmsy10', style='normal', variant='normal', weight=400, stretch='normal', size='scalable')) = 10.05
        [stdlog] 2023-04-20 10:07:03,998 matplotlib.font_manager DEBUG| findfont: score(FontEntry(fname='/home/janrichter/.pyenv/versions/avocado/lib/python3.10/site-packages/matplotlib/mpl-data/fonts/ttf/STIXNonUni.ttf', name='STIXNonUnicode', style='normal', variant='normal', weight=400, stretch='normal', size='scalable')) = 10.05
        [stdlog] 2023-04-20 10:07:03,998 matplotlib.font_manager DEBUG| findfont: score(FontEntry(fname='/home/janrichter/.pyenv/versions/avocado/lib/python3.10/site-packages/matplotlib/mpl-data/fonts/ttf/STIXGeneralBolIta.ttf', name='STIXGeneral', style='italic', variant='normal', weight=700, stretch='normal', size='scalable')) = 11.335
        [stdlog] 2023-04-20 10:07:03,998 matplotlib.font_manager DEBUG| findfont: score(FontEntry(fname='/home/janrichter/.pyenv/versions/avocado/lib/python3.10/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSansMono-Bold.ttf', name='DejaVu Sans Mono', style='normal', variant='normal', weight=700, stretch='normal', size='scalable')) = 10.335
        [stdlog] 2023-04-20 10:07:03,998 matplotlib.font_manager DEBUG| findfont: score(FontEntry(fname='/home/janrichter/.pyenv/versions/avocado/lib/python3.10/site-packages/matplotlib/mpl-data/fonts/ttf/STIXNonUniBol.ttf', name='STIXNonUnicode', style='normal', variant='normal', weight=700, stretch='normal', size='scalable')) = 10.335
        ...
