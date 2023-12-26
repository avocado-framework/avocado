HTML results Plugin
===================

This optional plugin creates beautiful human readable results.

To install the HTML plugin from pip, use::

    $ pip install avocado-framework-plugin-result-html

Once installed it produces the results in job results dir::

    $ avocado run avocado/examples/tests/sleeptest.py avocado/examples/tests/failtest.py
    JOB ID     : 480461f676fcf2a8c1c449ca1252be9521ffcceb
    JOB LOG    : $HOME/avocado/job-results/job-2021-09-30T16.02-480461f/job.log
    (2/2) avocado/examples/tests/failtest.py:FailTest.test: STARTED
    (1/2) avocado/examples/tests/sleeptest.py:SleepTest.test: STARTED
    (2/2) avocado/examples/tests/failtest.py:FailTest.test: FAIL: This test is supposed to fail (0.04 s)
    (1/2) avocado/examples/tests/sleeptest.py:SleepTest.test: PASS (1.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB HTML   : $HOME/avocado/job-results/job-2021-09-30T16.02-480461f/results.html
    JOB TIME   : 2.76 s


This can be disabled via ``--disable-html-job-result``. One can also specify a
custom location via ``--html`` . Last but not least ``--open-browser`` can be used to
start browser automatically once the job finishes.
