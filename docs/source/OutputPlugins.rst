.. _output-plugins:

Output Plugins
==============

A test runner must provide an assortment of ways to clearly communicate results
to interested parties, be them humans or machines. The types of output that
avocado is interested in produce are:

* Human Readable:
    Textual output that humans can make sense of. Not meant to be
    parsed by scripts whatsoever.
* Machine Readable:
    Data structure representation that can be easily parsed
    and/or stored by programs. This is how the test suite is
    supposed to interact with other programs.

As an example of human readable output, we have the dots that python unittests
print while executing tests::

    $ unittests/avocado/test_unittest.py 
    ss..........
    ----------------------------------------------------------------------
    Ran 12 tests in 1.243s

    OK (skipped=2)

Or the more verbose avocado output::

    $ scripts/avocado run "sleeptest failtest synctest"
    DEBUG LOG: /home/lmr/Code/avocado/logs/run-2014-04-24-18.17.52/debug.log
    TOTAL TESTS: 3
    (1/3) sleeptest.1:  PASS (1.09 s)
    (2/3) failtest.1:  FAIL (0.10 s)
    (3/3) synctest.1:  PASS (1.98 s)
    TOTAL PASSED: 2
    TOTAL ERROR: 0
    TOTAL FAILED: 1
    TOTAL SKIPPED: 0
    TOTAL WARNED: 0
    ELAPSED TIME: 3.17 s

The most important thing is to remember that programs should never need to parse
human output to figure out what happened with your test run.

Machine readable output - xunit
-------------------------------

The default machine readable output in avocado is
`xunit <http://help.catchsoftware.com/display/ET/JUnit+Format>`__, an xml format
that contains test results in a structured form, and are used by other test
automation projects, such as `jenkins <http://jenkins-ci.org/>`__. If you want
to make avocado to generate xunit output in the standard output of the runner,
simply use::

    $ scripts/avocado --xunit run "sleeptest failtest synctest"
    <?xml version="1.0" encoding="UTF-8"?>
    <testsuite name="avocado" tests="3" errors="0" failures="1" skip="0" time="2.88632893562" timestamp="2014-04-24 18:25:39.545588">
        <testcase classname="sleeptest" name="sleeptest.1" time="1.10091400146"/>
        <testcase classname="failtest" name="failtest.1" time="0.0921177864075">
            <failure><![CDATA[This test is supposed to fail]]></failure>
        </testcase>
        <testcase classname="synctest" name="synctest.1" time="1.69329714775"/>

Implementing other output formats
---------------------------------

If you are looking to implement a new machine/human readable output format,
you can refer to :mod:`avocado.plugins.xunit`. In a nutshell, you have to
implement a class that inherits from :class:`avocado.result.TestResult` and
implements all public methods, that perform actions (write to a file/stream)
for each test states. You can take a look at :doc:`Plugins` for more info
on how to write plugins.