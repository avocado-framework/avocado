.. _get-started:

=============================
Getting started guide - users
=============================

If you want to simply use avocado as a test runner/test API, you can install a
distro package. For Fedora, you can look
at `lmr's autotest COPR`_, while for Ubuntu, you can look
at `lmr's autotest PPA`_.

.. _lmr's autotest COPR: http://copr.fedoraproject.org/coprs/lmr/Autotest
.. _lmr's autotest PPA: https://launchpad.net/~lmr/+archive/autotest

Avocado is primarily being developed on Fedora boxes, but we are making
reasonable efforts that Ubuntu users can use and develop avocado well.

Installing avocado - Fedora
---------------------------

You can install the rpm package by performing the following commands:

::

    sudo curl http://copr.fedoraproject.org/coprs/lmr/Autotest/repo/fedora-20-i386/ > /etc/yum.repos.d/autotest.repo
    sudo yum update
    sudo yum install avocado

Installing avocado - Ubuntu
---------------------------

You can install the debian package by performing the following commands:

::

    sudo add-apt-repository ppa:lmr/autotest
    sudo apt-get update
    sudo apt-get install avocado


Running the avocado test runner
-------------------------------

The test runner is designed to conveniently run tests on your laptop. The tests
you can run are:

* Tests written in python, using the avocado API, which we'll call `native`.
* Any executable in your box, really. The criteria for PASS/FAIL is the return
  code of the executable. If it returns 0, the test PASSed, if it returned
  != 0, it FAILed. We'll call those tests `dropin`.

Avocado looks for avocado "native" tests in some locations, the main one is in
the config file ``/etc/avocado/settings.ini``, section ``runner``, ``test_dir``
key. You can list tests by::

    $ avocado list
    Tests available:
        failtest
        sleeptest
        synctest

You can run them using the subcommand ``run``::

    $ scripts/avocado run sleeptest
    DEBUG LOG: /home/lmr/Code/avocado/logs/run-2014-04-23-19.06.39/debug.log
    TOTAL TESTS: 1
    (1/1) sleeptest.1:  PASS (1.09 s)
    TOTAL PASSED: 1
    TOTAL ERROR: 0
    TOTAL FAILED: 0
    TOTAL SKIPPED: 0
    TOTAL WARNED: 0
    ELAPSED TIME: 1.09 s

You can run any number of test in an arbitrary order, as well as mix and match
native tests and dropin tests::

    $ echo '#!/bin/bash' > /tmp/script_that_passes.sh
    $ echo 'true' >> /tmp/script_that_passes.sh
    $ scripts/avocado run "failtest sleeptest synctest failtest synctest /tmp/script_that_passes.sh"
    DEBUG LOG: /home/lmr/Code/avocado/logs/run-2014-04-23-19.16.46/debug.log
    TOTAL TESTS: 6
    (1/6) failtest.1:  FAIL (0.09 s)
    (2/6) sleeptest.1:  PASS (1.09 s)
    (3/6) synctest.1:  PASS (2.33 s)
    (4/6) failtest.2:  FAIL (0.10 s)
    (5/6) synctest.2:  PASS (1.94 s)
    (6/6) script_that_passes.1:  PASS (0.11 s)
    TOTAL PASSED: 4
    TOTAL ERROR: 0
    TOTAL FAILED: 2
    TOTAL SKIPPED: 0
    TOTAL WARNED: 0
    ELAPSED TIME: 5.67 s
