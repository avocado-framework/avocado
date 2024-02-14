Introduction
============

Avocado Hello World
-------------------

You should first experience Avocado by using the test runner, that is, the
command line tool that will conveniently run your tests and collect their
results.

To do so, please run ``avocado`` with the ``run`` sub-command followed by a
test reference, which could be either a path to the file, or a recognizable
name::

    $ avocado run /bin/true
    JOB ID     : 89b5d609d4832c784f04cf14f4ec2d17917d419a
    JOB LOG    : $HOME/avocado/job-results/job-2023-09-06T15.52-89b5d60/job.log
     (1/1) /bin/true: STARTED
     (1/1) /bin/true: PASS (0.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB HTML   : $HOME/avocado/job-results/job-2023-09-06T15.52-89b5d60/results.html
    JOB TIME   : 1.49 s

You probably noticed that we used ``/bin/true`` as a test, and in
accordance with our expectations, it passed! These are known as
`executable tests` (``exec-test``), but there is also another type of
test, which we call `instrumented tests` . See more at `test-types` or
just keep reading.


Running a job with multiple tests
---------------------------------

You can run any number of test in an arbitrary order, as well as mix and match
instrumented and executable tests::

    $ avocado run examples/tests/sleeptest.py examples/tests/failtest.py /bin/true
    JOB ID     : 2391dddf53b950631589bd1d44a5a6fdd023b400
    JOB LOG    : $HOME/avocado/job-results/job-2021-09-27T16.35-2391ddd/job.log
     (3/3) /bin/true: STARTED
     (1/3) examples/tests/sleeptest.py:SleepTest.test: STARTED
     (3/3) /bin/true: PASS (0.01 s)
     (2/3) examples/tests/failtest.py:FailTest.test: STARTED
     (2/3) examples/tests/failtest.py:FailTest.test: FAIL: This test is supposed to fail (0.02 s)
     (1/3) examples/tests/sleeptest.py:SleepTest.test: PASS (1.01 s)
    RESULTS    : PASS 2 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 4.19 s

.. note:: Although in most cases running ``avocado run $test1 $test3 ...`` is
          fine, it can lead to argument vs. test name clashes. The safest
          way to execute tests is ``avocado run --$argument1 --$argument2
          -- $test1 $test2``. Everything after ``--`` will be considered
          positional arguments, therefore test names (in case of
          ``avocado run``)


Using a different runner
------------------------

Currently Avocado has only one runner: ``nrunner`` (the new runner)
But some plugins may use their own runners.
You can find a list of current runners installed with the
``avocado plugins`` command::

  $ avocado plugins
  Plugins that run test suites on a job (runners):
  nrunner nrunner based implementation of job compliant runner

During the test execution, you can select the runner using the option
``--suite-runner``, where the default is the nrunner one::

  $ avocado run --suite-runner='runner' /bin/true


Interrupting tests
------------------

.. _signal_hanlders:

Sending Signals
~~~~~~~~~~~~~~~

To interrupt a job execution a user can press ``ctrl+c`` which after a single
press sends ``SIGTERM`` to the main test's process and waits for it to finish.  If
this does not help user can press ``ctrl+c`` again (after 2s grace period)
which destroys the test's process ungracefully and safely finishes the job
execution always providing the test results.

Interrupting the job on first fail (failfast)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Avocado ``run`` command has the option ``--failfast`` to exit the job as
soon as possible.

Due to our current runner architecture, tests are executed in parallel by
default.  The ``--failfast`` option work on the best effort to cancel tests
that have not started yet. To replicate the same behavior as the legacy runner,
use ``--max-parallel-tasks=1`` to limit the number of tasks executed in
parallel::

    $ avocado run --failfast --max-parallel-tasks=1 /bin/true /bin/false /bin/true /bin/true
    JOB ID     : 76bfe0e5cfa5efac3ab6881ee501cc5d4b69f913
    JOB LOG    : $HOME/avocado/job-results/job-2021-09-27T16.41-76bfe0e/job.log
     (1/4) /bin/true: STARTED
     (1/4) /bin/true: PASS (0.01 s)
     (2/4) /bin/false: STARTED
     (2/4) /bin/false: FAIL (0.01 s)
    Interrupting job (failfast).
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 2 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 1.57 s

The default behavior, that is, when ``--failfast`` is **not** set, is
to try to execute all tests in a job, regardless individual of test failures.

.. note:: Avocado versions 80.0 and earlier allowed replayed jobs to override
          the failfast configuration by setting ``--failfast=off`` in a
          ``avocado replay ..`` command line.  This is no longer possible.

.. _the_hint_files:

The hint files
--------------

Avocado team has added support to the "hint files". This feature is present
since Avocado #78 and is a configuration file that you can add to your project
root folder to help Avocado on the "test resolution" phase.

The idea is that, you know more about your tests than anybody else. And you can
specify where your tests are, and what type (kind) they are. You just have to
add a ``.avocado.hint`` in your root folder with the section ``[kinds]`` and one
section for each kind that you are using.

On the specific test type section, you can specify 3 options: ``uri``, ``args`` and
``kwargs``.

.. note:: Some test types will convert ``kwargs`` into variable environments.
 Please check the documentation of the test type that you are using.

You can also use the keyword ``$testpath`` in any of the options inside the test
type section. Avocado will replace ``$testpath`` with your test path, after the
expansion.

For instance, below you will find a hint file example where we have only one
test type ``TAP``:

.. literalinclude:: ../../../../../examples/hint-files/.avocado.hint.example

Let's suppose that you have 2 tests that matches ``./tests/unit/*.sh``:

* ``./tests/unit/foo.sh``
* ``./tests/unit/bar.sh``

Avocado will run each one as a ``TAP`` test, as you desired.

.. note:: Please, keep in mind that hint files needs absolute paths when
   defining tests inside the ``[kinds]`` section.

Since Avocado's next runner is capable of running tests not only in a
subprocess but also in more isolated environments such as Podman containers,
sending custom environment variables to the task executor can be achieved by
using the ``kwargs`` parameter. Use a comma-separated list of variables here
and Avocado will make sure your tests will receive those variables (regardless
of the spawner type).

Ignoring missing test references
--------------------------------

When you provide a list of test references, Avocado will try to resolve all of
them to tests. If one or more test references can not be resolved to tests, the
Job will not be created. Example::

    $ avocado run examples/tests/passtest.py badtest.py
    No tests found for given test references: badtest.py
    Try 'avocado -V list badtest.py' for details

But if you want to execute the Job anyway, with the tests that could be
resolved, you can use ``--ignore-missing-references``, a boolean command-line
option. The same message will appear in the UI, but the Job will be executed::

    $ avocado run examples/tests/passtest.py badtest.py --ignore-missing-references
    JOB ID     : e6d1f4d21d6a5e2e039f1acd1670a6882144c189
    JOB LOG    : $HOME/avocado/job-results/job-2021-09-27T16.50-e6d1f4d/job.log
     (1/1) examples/tests/passtest.py:PassTest.test: STARTED
     (1/1) examples/tests/passtest.py:PassTest.test: PASS (0.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 1.49 s

Runner outputs
--------------

A test runner must provide an assortment of ways to clearly communicate results
to interested parties, be them humans or machines.

.. note:: There are several optional result plugins, you can find them in
   :ref:`result-plugins`.

Results for human beings
~~~~~~~~~~~~~~~~~~~~~~~~

Avocado has two different result formats that are intended for human beings:

* Its default UI, which shows the live test execution results on a command
  line, text based, UI.
* The HTML report, which is generated after the test job finishes running.

.. note:: The HTML report needs the ``html`` plugin enabled that is an optional
  plugin.

A regular run of Avocado will present the test results in a live fashion, that
is, the job and its test(s) results are constantly updated::

    $ avocado run examples/tests/sleeptest.py examples/tests/failtest.py
    JOB ID     : 2e83086e5d3f82dd68bdc8885e7cce1cebec5f27
    JOB LOG    : $HOME/avocado/job-results/job-2021-09-27T17.00-2e83086/job.log
     (1/2) examples/tests/sleeptest.py:SleepTest.test: STARTED
     (2/2) examples/tests/failtest.py:FailTest.test: STARTED
     (2/2) examples/tests/failtest.py:FailTest.test: FAIL: This test is supposed to fail (0.02 s)
     (1/2) examples/tests/sleeptest.py:SleepTest.test: PASS (1.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB HTML   : $HOME/avocado/job-results/job-2021-09-27T17.00-2e83086/results.html
    JOB TIME   : 2.80 s

The most important thing is to remember that programs should never need to
parse human output to figure out what happened to a test job run.

As you can see, Avocado will print a nice UI with the job summary on the
console. If you would like to inspect a detailed output of your tests, you can
visit the folder: ``$HOME/avocado/job-results/latest/`` or a specific job
folder.

Results for machine
~~~~~~~~~~~~~~~~~~~

Another type of results are those intended to be parsed by other applications.
Several standards exist in the test community, and Avocado can in theory
support pretty much every result standard out there.

Out of the box, Avocado supports a couple of machine readable results. They are
always generated and stored in the results directory in ``results.$type`` files,
but you can ask for a different location too.

Currently, you can find three different formats available on this folder:
**xUnit (XML)**, **JSON** and **TAP**.

 **1. xUnit:**

The default machine readable output in Avocado is `xunit
<http://help.catchsoftware.com/display/ET/JUnit+Format>`__.

xUnit is an XML format that contains test results in a structured form, and are
used by other test automation projects, such as `jenkins
<http://jenkins-ci.org/>`__. If you want to make Avocado to generate xunit
output in the standard output of the runner, simply use::

    $ avocado run examples/tests/sleeptest.py examples/tests/failtest.py --xunit -
    <?xml version="1.0" encoding="UTF-8"?>
    <testsuite name="job-2023-12-21T08.42-0af6e08" tests="2" errors="0" failures="1" skipped="0" time="1.029" timestamp="2023-12-21T08:42:56.070128">
    	<testcase classname="FailTest" name="examples/tests/failtest.py:FailTest.test" time="0.021">
    		<failure type="TestFail" message="This test is supposed to fail"><![CDATA[Traceback (most recent call last):
      File "$HOME/src/avocado/avocado/avocado/core/test.py", line 646, in _run_test
        raise details
      File "$HOME/src/avocado/avocado/avocado/core/test.py", line 633, in _run_test
        testMethod()
      File "$HOME/src/avocado/avocado/examples/tests/failtest.py", line 16, in test
        self.fail("This test is supposed to fail")
      File "$HOME/src/avocado/avocado/avocado/core/test.py", line 785, in wrapper
        return func(actual_message)
               ^^^^^^^^^^^^^^^^^^^^
      File "$HOME/src/avocado/avocado/avocado/core/test.py", line 801, in fail
        raise exceptions.TestFail(msg)
    avocado.core.exceptions.TestFail: This test is supposed to fail
    ]]></failure>
    		<system-out><![CDATA[[stdlog] 2023-12-21 08:42:54,720 avocado.test test             L0313 INFO | INIT 1-examples/tests/failtest.py:FailTest.test
    [stdlog] 2023-12-21 08:42:54,721 avocado.test parameters       L0141 DEBUG| PARAMS (key=timeout, path=*, default=None) => None
    [stdlog] 2023-12-21 08:42:54,721 avocado.test parameters       L0141 DEBUG| PARAMS (key=timeout_factor, path=*, default=1.0) => 1.0
    [stdlog] 2023-12-21 08:42:54,721 avocado.test test             L0345 DEBUG| Test metadata:
    [stdlog] 2023-12-21 08:42:54,721 avocado.test test             L0347 DEBUG|   filename: $HOME/src/avocado/avocado/examples/tests/failtest.py
    [stdlog] 2023-12-21 08:42:54,721 avocado.test test             L0353 DEBUG|   teststmpdir: /var/tmp/avocado_tx32gp2p
    [stdlog] 2023-12-21 08:42:54,721 avocado.test test             L0354 DEBUG|   original timeout: None
    [stdlog] 2023-12-21 08:42:54,721 avocado.test test             L0355 DEBUG|   timeout factor: 1.0
    [stdlog] 2023-12-21 08:42:54,721 avocado.test test             L0356 DEBUG|   actual timeout: None
    [stdlog] 2023-12-21 08:42:54,722 avocado.test test             L0548 INFO | START 1-examples/tests/failtest.py:FailTest.test
    [stdlog] 2023-12-21 08:42:54,722 avocado.test stacktrace       L0040 ERROR| 
    [stdlog] 2023-12-21 08:42:54,722 avocado.test stacktrace       L0042 ERROR| Reproduced traceback from: $HOME/src/avocado/avocado/avocado/core/test.py:638
    [stdlog] 2023-12-21 08:42:54,723 avocado.test stacktrace       L0049 ERROR| Traceback (most recent call last):
    [stdlog] 2023-12-21 08:42:54,723 avocado.test stacktrace       L0049 ERROR|   File "$HOME/src/avocado/avocado/examples/tests/failtest.py", line 16, in test
    [stdlog] 2023-12-21 08:42:54,723 avocado.test stacktrace       L0049 ERROR|     self.fail("This test is supposed to fail")
    [stdlog] 2023-12-21 08:42:54,723 avocado.test stacktrace       L0049 ERROR|   File "$HOME/src/avocado/avocado/avocado/core/test.py", line 785, in wrapper
    [stdlog] 2023-12-21 08:42:54,723 avocado.test stacktrace       L0049 ERROR|     return func(actual_message)
    [stdlog] 2023-12-21 08:42:54,723 avocado.test stacktrace       L0049 ERROR|            ^^^^^^^^^^^^^^^^^^^^
    [stdlog] 2023-12-21 08:42:54,723 avocado.test stacktrace       L0049 ERROR|   File "$HOME/src/avocado/avocado/avocado/core/test.py", line 801, in fail
    [stdlog] 2023-12-21 08:42:54,723 avocado.test stacktrace       L0049 ERROR|     raise exceptions.TestFail(msg)
    [stdlog] 2023-12-21 08:42:54,723 avocado.test stacktrace       L0049 ERROR| avocado.core.exceptions.TestFail: This test is supposed to fail
    [stdlog] 2023-12-21 08:42:54,723 avocado.test stacktrace       L0050 ERROR| 
    [stdlog] 2023-12-21 08:42:54,723 avocado.test test             L0642 DEBUG| Local variables:
    [stdlog] 2023-12-21 08:42:54,735 avocado.test test             L0645 DEBUG|  -> self <class 'failtest.FailTest'>: 1-examples/tests/failtest.py:FailTest.test
    [stdlog] 2023-12-21 08:42:54,736 avocado.test test             L0740 ERROR| FAIL 1-examples/tests/failtest.py:FailTest.test -> TestFail: This test is supposed to fail
    [stdlog] 2023-12-21 08:42:54,736 avocado.test test             L0733 INFO | 
    ]]></system-out>
    	</testcase>
    	<testcase classname="SleepTest" name="examples/tests/sleeptest.py:SleepTest.test" time="1.008"/>
    </testsuite>


.. note:: The dash ``-`` in the option ``--xunit``, it means that the xunit result
          should go to the standard output.

.. note:: In case your tests produce very long outputs, you can limit the
          number of embedded characters by
          ``--xunit-max-test-log-chars``. If the output in the log file is
          longer it only attaches up-to max-test-log-chars characters
          one half starting from the beginning of the content, the other
          half from the end of the content.


**2. JSON:**


`JSON <https://www.json.org/>`__ is a widely used data exchange format. The JSON
Avocado plugin outputs job information, similarly to the xunit output plugin::

    $ avocado run examples/tests/sleeptest.py examples/tests/failtest.py --json -
    {
        "cancel": 0,
        "debuglog": "$HOME/avocado/job-results/job-2024-02-08T16.24-bee291e/job.log",
        "errors": 0,
        "failures": 1,
        "interrupt": 0,
        "job_id": "bee291e496e7a54b3e81e3836abd860aa779d37b",
        "pass": 1,
        "skip": 0,
        "start": "2024-02-08 16:24:48.169658",
        "tests": [
            {
                "actual_time_end": 1707405889.5167582,
                "actual_time_start": 1707405889.207349,
                "fail_reason": "This test is supposed to fail",
                "id": "2-examples/tests/failtest.py:FailTest.test",
                "logdir": "$HOME/avocado/job-results/job-2024-02-08T16.24-bee291e/test-results/2-examples_tests_failtest.py_FailTest.test",
                "logfile": "$HOME/avocado/job-results/job-2024-02-08T16.24-bee291e/test-results/2-examples_tests_failtest.py_FailTest.test/debug.log",
                "name": "examples/tests/failtest.py:FailTest.test",
                "status": "FAIL",
                "tags": {
                    "failure_expected": null
                },
                "time_elapsed": 0.038685322972014546,
                "time_end": 889039.845678904,
                "time_start": 889039.806993581,
                "whiteboard": ""
            },
            {
                "actual_time_end": 1707405890.2360377,
                "actual_time_start": 1707405889.2069798,
                "fail_reason": "<unknown>",
                "id": "1-examples/tests/sleeptest.py:SleepTest.test",
                "logdir": "$HOME/avocado/job-results/job-2024-02-08T16.24-bee291e/test-results/1-examples_tests_sleeptest.py_SleepTest.test",
                "logfile": "$HOME/avocado/job-results/job-2024-02-08T16.24-bee291e/test-results/1-examples_tests_sleeptest.py_SleepTest.test/debug.log",
                "name": "examples/tests/sleeptest.py:SleepTest.test",
                "status": "PASS",
                "tags": {},
                "time_elapsed": 1.011205994989723,
                "time_end": 889040.816592906,
                "time_start": 889039.805386911,
                "whiteboard": ""
            }
        ],
        "time": 1.0498913179617375,
        "total": 2,
        "warn": 0
    }


.. note:: The dash ``-`` in the option ``--json``, it means that the xunit result
          should go to the standard output.

Bear in mind that there's no documented standard for the Avocado JSON result
format. This means that it will probably grow organically to accommodate newer
Avocado features. A reasonable effort will be made to not break backwards
compatibility with applications that parse the current form of its JSON result.


**3. TAP:**

Provides the basic `TAP <https://testanything.org/>`__ (Test Anything Protocol)
results, currently in v12. Unlike most existing Avocado machine readable
outputs this one is streamlined (per test results)::

    $ avocado run examples/tests/sleeptest.py --tap -
    1..1
    ok 1 examples/tests/sleeptest.py:SleepTest.test


**4. Beaker:**

When avocaodo finds itself running inside a beaker task the
beaker_report plugin will send the test results and log files to the
beaker lab controller.  Happens automatically, no configuration
required.  Check the `project website <https://beaker-project.org/>`__
for more information on beaker.


Using the option --show
~~~~~~~~~~~~~~~~~~~~~~~

Probably, you frequently want to look straight at the job log, without
switching screens or having to "tail" the job log.

In order to do that, you can use ``avocado --show=job run ...``::

    $ avocado --show=job run examples/tests/sleeptest.py
    ...
    
    avocado.job: Job ID: c9ca6a96d34fd0355f5f121af7fa87eef734a196
    avocado.job:
    avocado.job: examples/tests/sleeptest.py:SleepTest.test: STARTED
    avocado.job: examples/tests/sleeptest.py:SleepTest.test: PASS
    avocado.job: More information in $HOME/avocado/job-results/job-2023-09-08T15.27-c9ca6a9/test-results/1-examples_tests_sleeptest.py_SleepTest.test
    avocado.job: Test results available in $HOME/avocado/job-results/job-2023-09-08T15.27-c9ca6a9


As you can see, the UI output is suppressed and only the job log is shown,
making this a useful feature for test development and debugging.

It's possible to silence all output to stdout (while keeping the error messages
being printed to stderr). One can then use the return code to learn about the
result::

    $ avocado --show=none run examples/tests/failtest.py
    $ echo $?
    1

In practice, this would usually be used by scripts that will in turn run
Avocado and check its results::

    #!/bin/bash
    ...
    $ avocado --show=none run /path/to/my/test.py
    if [ $? == 0 ]; then
       echo "great success!"
    elif
       ...

more details regarding exit codes in `Exit Codes` section.

Multiple results at once
~~~~~~~~~~~~~~~~~~~~~~~~

You can have multiple results formats at once, as long as only one of them uses
the standard output. For example, it is fine to use the xunit result on stdout
and the JSON result to output to a file::

    $ avocado run examples/tests/sleeptest.py /bin/true --xunit - --json /tmp/result.json
    <?xml version="1.0" encoding="UTF-8"?>
    <testsuite name="job-2023-12-21T08.46-a4f410d" tests="2" errors="0" failures="0" skipped="0" time="1.020" timestamp="2023-12-21T08:46:25.268311">
    	<testcase classname="&lt;unknown&gt;" name="/bin/true" time="0.011"/>
    	<testcase classname="SleepTest" name="examples/tests/sleeptest.py:SleepTest.test" time="1.008"/>
    </testsuite>

    $ cat /tmp/result.json
    {
        "cancel": 0,
        "debuglog": "$HOME/avocado/job-results/job-2023-12-21T08.46-a4f410d/job.log",
        "errors": 0,
        "failures": 0,
        "interrupt": 0,
        "job_id": "a4f410de7969bc8d6148712796e027b110027fa3",
        "pass": 2,
        "skip": 0,
        "start": "2023-12-21 08:46:21.078811",
    ...
    }

But you won't be able to do the same without the ``--json`` flag passed to
the program::

    avocado run examples/tests/sleeptest.py /bin/true --xunit - --json  -
    avocado run: error: argument --json: Options --xunit --json are trying to
    use stdout simultaneously. Please set at least one of them to a file to
    avoid conflicts

That's basically the only rule, and a sane one, that you need to follow.

.. note:: Avocado support "paginator" option, which, on compatible
  terminals, basically pipes the colored output to ``less`` to simplify
  browsing of the produced output. You an enable it with ``--enable-paginator``.

.. _sysinfo-collection:

Sysinfo collection
------------------

Avocado comes with a ``sysinfo`` plugin, which automatically gathers some
system information per each job or even between tests. This is very useful
when later we want to know what caused the test's failure. This system
is configurable but we provide a sane set of defaults for you.

In the default Avocado configuration (``/etc/avocado/avocado.conf``) there
is a section ``sysinfo.collect`` where you can enable/disable the sysinfo
collection as well as configure the basic environment. In
``sysinfo.collectibles`` section you can define basic paths of where
to look for what commands/tasks should be performed before/during
the sysinfo collection. Avocado supports three types of tasks:

1. commands - file with new-line separated list of commands to be executed
   before and after the job/test (single execution commands). It is possible
   to set a timeout which is enforced per each executed command in
   ``[sysinfo.collect]`` by setting "commands_timeout" to a positive number.
   You can also use the environment variable ``AVOCADO_SYSINFODIR`` which points
   to the sysinfo directory in results.
2. fail_commands - similar to commands, but gets executed only when the test
   fails.
3. files - file with new-line separated list of files to be copied.
4. fail_files - similar to files, but copied only when the test fails.
5. profilers - file with new-line separated list of commands to be executed
   before the job/test and killed at the end of the job/test (follow-like
   commands).

Additionally this plugin tries to follow the system log via ``journalctl``
if available.

By default these are collected per-job but you can also run them per-test by
setting ``per_test = True`` in the ``sysinfo.collect`` section.

The sysinfo is enabled by default and can also be disabled on the cmdline if
needed by ``--disable-sysinfo``.

After the job execution you can find the collected information in
``$RESULTS/sysinfo`` of ``$RESULTS/test-results/$TEST/sysinfo``. They
are categorized into ``pre``, ``post`` and ``profile`` folders and
the filenames are safely-escaped executed commands or file-names.
You can also see the sysinfo in html results when you have html
results plugin enabled.

It is also possible to save only the files / commands which were changed
during the course of the test, in the ``post`` directory, using the setting
``optimize = True`` in the ``sysinfo.collect`` section. This collects all
sysinfo on ``pre``, but saves only changed ones on ``post``. It is set to
False by default.

.. warning:: If you are using Avocado from sources, you need to manually place
    ``commands``/``fail_commands``/``fail_files``/``files``/``profilers`` into
    the ``/etc/avocado/sysinfo`` directory or adjust the paths in your
    ``avocado.conf``.
