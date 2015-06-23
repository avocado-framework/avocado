.. _output-plugins:

Result Formats
==============

A test runner must provide an assortment of ways to clearly communicate results
to interested parties, be them humans or machines. The types of output that
Avocado is interested in produce are:

* Human Readable:
    Textual output that humans can make sense of. Not meant to be
    parsed by scripts whatsoever.
* Machine Readable:
    Data structure representation that can be easily parsed
    and/or stored by programs. This is how the test suite is
    supposed to interact with other programs.

As an example of human readable output, we have the dots that Python unittests
print while executing tests::

    $ unittests/avocado/test_unittest.py
    ss..........
    ----------------------------------------------------------------------
    Ran 12 tests in 1.243s

    OK (skipped=2)

Or the more verbose Avocado output::

    $ avocado run sleeptest failtest synctest
    JOB ID    : 5ffe479262ea9025f2e4e84c4e92055b5c79bdc9
    JOB LOG   : $HOME/avocado/job-results/job-2014-08-12T15.57-5ffe4792/job.log
    JOB HTML  : $HOME/avocado/job-results/job-2014-08-12T15.57-5ffe4792/html/results.html
    TESTS     : 3
    (1/3) sleeptest.1: PASS (1.01 s)
    (2/3) failtest.1: FAIL (0.00 s)
    (3/3) synctest.1: PASS (1.98 s)
    PASS      : 1
    ERROR     : 1
    FAIL      : 1
    SKIP      : 0
    WARN      : 0
    INTERRUPT : 0
    TIME      : 3.17 s

The most important thing is to remember that programs should never need to parse
human output to figure out what happened with your test run.

Machine readable output - xunit
-------------------------------

The default machine readable output in Avocado is
`xunit <http://help.catchsoftware.com/display/ET/JUnit+Format>`__, an xml format
that contains test results in a structured form, and are used by other test
automation projects, such as `jenkins <http://jenkins-ci.org/>`__. If you want
to make Avocado to generate xunit output in the standard output of the runner,
simply use::

    $ scripts/avocado --xunit - run "sleeptest failtest synctest"
    <?xml version="1.0" encoding="UTF-8"?>
    <testsuite name="avocado" tests="3" errors="0" failures="1" skip="0" time="2.88632893562" timestamp="2014-04-24 18:25:39.545588">
        <testcase classname="sleeptest" name="sleeptest.1" time="1.10091400146"/>
        <testcase classname="failtest" name="failtest.1" time="0.0921177864075">
            <failure><![CDATA[This test is supposed to fail]]></failure>
        </testcase>
        <testcase classname="synctest" name="synctest.1" time="1.69329714775"/>

Note the dash `-` in the option `--xunit`, it means that the output
goes through the standard output.

Machine readable output - json
------------------------------

`JSON <http://www.json.org/>`__ is a widely used data exchange format. The
json Avocado plugin outputs job information, similarly to the xunit output
plugin::

    $ scripts/avocado --json - run "sleeptest failtest synctest"
    {"tests": [{"test": "sleeptest.1", "url": "sleeptest", "status": "PASS", "time": 1.4282619953155518}, {"test": "failtest.1", "url": "failtest", "status": "FAIL", "time": 0.34017300605773926}, {"test": "synctest.1", "url": "synctest", "status": "PASS", "time": 2.109131097793579}], "errors": 0, "skip": 0, "time": 3.87756609916687, "debuglog": "$HOME/avocado/logs/run-2014-06-11-01.35.15/debug.log", "pass": 2, "failures": 1, "total": 3}

Note the dash `-` in the option `--json`, it means that the output
goes through the standard output.

Silent output
-------------

If you are not interested in output, you can suppress it by using
the command line option `--silent`. The tests will be performed as expected,
with logs being created, but the human output will not be displayed.

Example::

    $ scripts/avocado --silent run failtest
    $ echo $?
    1

Multiple output plugins
-----------------------

You can enable multiple output plugins at once, as long as only one of them
uses the standard output. For example, it is fine to use the xunit plugin on
stdout and the JSON plugin to output to a file::

    $ scripts/avocado --xunit - --json /tmp/result.json run "sleeptest synctest"
    <?xml version="1.0" encoding="UTF-8"?>
    <testsuite name="avocado" tests="2" errors="0" failures="0" skip="0" time="3.21392536163" timestamp="2014-06-11 01:49:35.858187">
        <testcase classname="sleeptest" name="sleeptest.1" time="1.34533214569"/>
        <testcase classname="synctest" name="synctest.1" time="1.86859321594"/>
    </testsuite>

    $ cat /tmp/result.json
    {"tests": [{"test": "sleeptest.1", "url": "sleeptest", "status": "PASS", "time": 1.345332145690918}, {"test": "synctest.1", "url": "synctest", "status": "PASS", "time": 1.8685932159423828}], "errors": 0, "skip": 0, "time": 3.213925361633301, "debuglog": "$HOME/avocado/logs/run-2014-06-11-01.49.35/debug.log", "pass": 2, "failures": 0, "total": 2}

But you won't be able to do the same without the --json flag passed to
the program::

    $ scripts/avocado --xunit - --json - run "sleeptest synctest"
    Avocado could not set --json and --xunit both to output to stdout.
    Please set the output flag of one of them to a file to avoid conflicts.

That's basically the only rule you need to follow.

Implementing other output formats
---------------------------------

If you are looking to implement a new machine/human readable output format,
you can refer to :mod:`avocado.core.plugins.xunit`. In a nutshell, you have to
implement a class that inherits from :class:`avocado.core.result.TestResult` and
implements all public methods, that perform actions (write to a file/stream)
for each test states. You can take a look at :doc:`Plugins` for more info
on how to write plugins.
