.. _get-started:

=============================
Getting started guide - users
=============================

If you want to simply use avocado as a test runner/test API, you can install a
distro package. For Fedora, you can look
at `lmr's autotest COPR`_, while for Ubuntu, you can look
at `lmr's avocado PPA`_.

.. _lmr's autotest COPR: http://copr.fedoraproject.org/coprs/lmr/Autotest
.. _lmr's avocado PPA: https://launchpad.net/~lmr/+archive/avocado

Avocado is primarily being developed on Fedora boxes, but we are making
reasonable efforts that Ubuntu users can use and develop avocado well.

Installing avocado - Fedora
===========================

You can install the rpm package by performing the following commands::

    sudo curl http://copr.fedoraproject.org/coprs/lmr/Autotest/repo/fedora-20/lmr-Autotest-fedora-20.repo -o /etc/yum.repos.d/autotest.repo
    sudo yum update
    sudo yum install avocado

Installing avocado - Ubuntu
===========================

You need to add the following lines::

    deb http://ppa.launchpad.net/lmr/avocado/ubuntu trusty main

To the file ``/etc/apt/sources.list``. After that you can install avocado by
performing the following commands::

    sudo apt-get update
    sudo apt-get install avocado

Using the avocado test runner
=============================

The test runner is designed to conveniently run tests on your laptop. The tests
you can run are:

* Tests written in python, using the avocado API, which we'll call `native`.
* Any executable in your box, really. The criteria for PASS/FAIL is the return
  code of the executable. If it returns 0, the test PASSed, if it returned
  != 0, it FAILed. We'll call those tests `simple tests`.

Native tests
------------

Avocado looks for avocado "native" tests in some locations, the main one is in
the config file ``/etc/avocado/avocado.conf``, section ``runner``, ``test_dir``
key. You can list tests by::

    $ avocado list
    Tests available:
        failtest
        sleeptest
        synctest

You can run them using the subcommand ``run``::

    $ avocado run sleeptest
    JOB ID : 381b849a62784228d2fd208d929cc49f310412dc
    JOB LOG: $HOME/avocado/job-results/job-2014-08-12T15.39-381b849a/job.log
    TESTS  : 1
    (1/1) sleeptest.1: PASS (1.01 s)
    PASS : 1
    ERROR: 0
    FAIL : 0
    SKIP : 0
    WARN : 0
    TIME : 1.01 s

Job ID
------

The Job ID is a SHA1 string that has some information encoded:

* Hostname
* ISO timestamp
* 64 bit integer

The idea is to have a unique identifier that can be used for job data, for
the purposes of joining on a single database results obtained by jobs run
on different systems.

Simple Tests
------------

You can run any number of test in an arbitrary order, as well as mix and match
native tests and simple tests::

    $ echo '#!/bin/bash' > /tmp/script_that_passes.sh
    $ echo 'true' >> /tmp/script_that_passes.sh
    $ chmod +x /tmp/script_that_passes.sh
    $ avocado run failtest sleeptest synctest failtest synctest /tmp/script_that_passes.sh
    JOB ID : 86911e49b5f2c36caeea41307cee4fecdcdfa121
    JOB LOG: $HOME/avocado/job-results/job-2014-08-12T15.42-86911e49/job.log
    TESTS  : 6
    (1/6) failtest.1: FAIL (0.00 s)
    (2/6) sleeptest.1: PASS (1.00 s)
    (3/6) synctest.1: ERROR (0.01 s)
    (4/6) failtest.2: FAIL (0.00 s)
    (5/6) synctest.2: ERROR (0.01 s)
    (6/6) /tmp/script_that_passes.sh.1: PASS (0.02 s)
    PASS : 2
    ERROR: 2
    FAIL : 2
    SKIP : 0
    WARN : 0
    TIME : 1.04 s

Debugging tests
---------------

When developing new tests, you frequently want to look at the straight
output of the job log in the stdout, without having to tail the job log.
In order to do that, you can use --show-job-log to the avocado test runner::

    $ scripts/avocado run examples/tests/sleeptest.py --show-job-log
    Not logging /proc/slabinfo (lack of permissions)
    START examples/tests/sleeptest.py

    Test instance parameters:
        id = examples/tests/sleeptest.py

    Default parameters:
        sleep_length = 1.0

    Test instance params override defaults whenever available

    Sleeping for 1.00 seconds
    Not logging /var/log/messages (lack of permissions)
    PASS examples/tests/sleeptest.py

    Not logging /proc/slabinfo (lack of permissions)

As you can see, the UI output is suppressed and only the job log goes to
stdout, making this a useful feature for test development/debugging. Some more
involved functionalities for the avocado runner will be discussed as
appropriate, during the introduction of important concepts.
