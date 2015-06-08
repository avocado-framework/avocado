.. _get-started:

===============
Getting Started
===============

The first step towards using Avocado is, quite obivously, installing it.

Installing Avocado
==================

Avocado is available in `RPM packages for Fedora`_, and `DEB packages for Ubuntu`_.

.. _RPM Packages For Fedora: http://copr.fedoraproject.org/coprs/lmr/Autotest
.. _DEB packages for Ubuntu: https://launchpad.net/~lmr/+archive/avocado

.. Note: the following text should instead reference the distro tiers levels

Avocado is primarily being developed on Fedora, but reasonable efforts
are being made to support other platforms such as Ubuntu.

Fedora
------

You can install the RPM packages by running the following commands::

    sudo curl http://copr.fedoraproject.org/coprs/lmr/Autotest/repo/fedora-20/lmr-Autotest-fedora-20.repo -o /etc/yum.repos.d/autotest.repo
    sudo yum update
    sudo yum install avocado

Don't mind the Fedora version here, the same repo file should work for newer distros.

Ubuntu
------

You can install Avocado by running the following commands::

    sudo echo "deb http://ppa.launchpad.net/lmr/avocado/ubuntu trusty main" >> /etc/apt/sources.list
    sudo apt-get update
    sudo apt-get install avocado

Generic installation from a GIT repository
------------------------------------------

First make sure you have a basic set of packages installed. The
following applies to Fedora based distributions, please adapt to
your platform::

    sudo yum install -y git gcc python-devel python-pip libvirt-devel libyaml-devel

Then to install Avocado from the git repository run::

    git clone git@github.com:avocado-framework/avocado.git
    cd avocado
    sudo pip install -r requirements.txt
    sudo python setup.py install

Note that `python` and `pip` should point to the Python interpreter version 2.7.x.
If you're having trouble to install, you can try again and use the command line
utilities `python2.7` and `pip2.7`.

For Debian users, use `apt-get` to install the proper dependencies that `yum` installs.

Using the Avocado test runner
=============================

The test runner is designed to conveniently run tests on your local machine. The types of
tests you can run are:

* Tests written in Python, using the Avocado API, which we'll call `instrumented`.
* Any executable in your box, really. The criteria for PASS/FAIL is the return
  code of the executable. If it returns 0, the test PASSes, if it returns anything
  else, it FAILs. We'll call those tests `simple tests`.

Listing tests
-------------

The ``avocado`` command line tool also has a ``list`` command, that lists the
known tests in a given path, be it a path to an individual test, or a path
to a directory. If no arguments provided, Avocado will inspect the contents
of the test location being used by Avocado (if you are in doubt about which
one is that, you may use ``avocado config --datadir``). The output looks like::

    $ avocado list
    INSTRUMENTED /usr/share/avocado/tests/abort.py
    INSTRUMENTED /usr/share/avocado/tests/datadir.py
    INSTRUMENTED /usr/share/avocado/tests/doublefail.py
    INSTRUMENTED /usr/share/avocado/tests/doublefree.py
    INSTRUMENTED /usr/share/avocado/tests/errortest.py
    INSTRUMENTED /usr/share/avocado/tests/failtest.py
    INSTRUMENTED /usr/share/avocado/tests/fiotest.py
    INSTRUMENTED /usr/share/avocado/tests/gdbtest.py
    INSTRUMENTED /usr/share/avocado/tests/gendata.py
    INSTRUMENTED /usr/share/avocado/tests/linuxbuild.py
    INSTRUMENTED /usr/share/avocado/tests/multiplextest.py
    INSTRUMENTED /usr/share/avocado/tests/passtest.py
    INSTRUMENTED /usr/share/avocado/tests/skiptest.py
    INSTRUMENTED /usr/share/avocado/tests/sleeptenmin.py
    INSTRUMENTED /usr/share/avocado/tests/sleeptest.py
    INSTRUMENTED /usr/share/avocado/tests/synctest.py
    INSTRUMENTED /usr/share/avocado/tests/timeouttest.py
    INSTRUMENTED /usr/share/avocado/tests/trinity.py
    INSTRUMENTED /usr/share/avocado/tests/warntest.py
    INSTRUMENTED /usr/share/avocado/tests/whiteboard.py

Here, ``INSTRUMENTED`` means that the files there are Python files with an Avocado
test class in them This means those tests have access to all Avocado APIs and
facilities. Let's try to list a directory with a bunch of executable shell
scripts::

    $ avocado list examples/wrappers/
    SIMPLE examples/wrappers/dummy.sh
    SIMPLE examples/wrappers/ltrace.sh
    SIMPLE examples/wrappers/perf.sh
    SIMPLE examples/wrappers/strace.sh
    SIMPLE examples/wrappers/time.sh
    SIMPLE examples/wrappers/valgrind.sh

Here, as covered in the previous section, ``SIMPLE`` means that those files are
executables, that Avocado will simply execute and return PASS or FAIL
depending on their return codes (PASS -> 0, FAIL -> any integer different
than 0). You can also provide the ``--verbose``, or ``-V`` flag to display files
that were detected but are not Avocado tests, along with summary information::

    $ avocado list examples/gdb-prerun-scripts/ -V
    Type       file
    NOT_A_TEST examples/gdb-prerun-scripts/README
    NOT_A_TEST examples/gdb-prerun-scripts/pass-sigusr1

    SIMPLE: 0
    INSTRUMENTED: 0
    BUGGY: 0
    MISSING: 0
    NOT_A_TEST: 2


Running Tests
-------------

You can run them using the subcommand ``run``::

    $ avocado run sleeptest
    JOB ID    : 381b849a62784228d2fd208d929cc49f310412dc
    JOB LOG   : $HOME/avocado/job-results/job-2014-08-12T15.39-381b849a/job.log
    JOB HTML  : $HOME/avocado/job-results/job-2014-08-12T15.39-381b849a/html/results.html
    TESTS     : 1
    (1/1) sleeptest.1: PASS (1.01 s)
    PASS      : 1
    ERROR     : 0
    FAIL      : 0
    SKIP      : 0
    WARN      : 0
    INTERRUPT : 0
    TIME : 1.01 s

Job ID
======

The Job ID is a SHA1 string that has some information encoded:

* Hostname
* ISO timestamp
* 64 bit integer

The idea is to have a unique identifier that can be used for job data, for
the purposes of joining on a single database results obtained by jobs run
on different systems.

Simple Tests
============

You can run any number of test in an arbitrary order, as well as mix and match
native tests and simple tests::

    $ echo '#!/bin/bash' > /tmp/script_that_passes.sh
    $ echo 'true' >> /tmp/script_that_passes.sh
    $ chmod +x /tmp/script_that_passes.sh
    $ avocado run failtest sleeptest synctest failtest synctest /tmp/script_that_passes.sh
    JOB ID    : 86911e49b5f2c36caeea41307cee4fecdcdfa121
    JOB LOG   : $HOME/avocado/job-results/job-2014-08-12T15.42-86911e49/job.log
    JOB HTML  : $HOME/avocado/job-results/job-2014-08-12T15.42-86911e49/html/results.html
    TESTS     : 6
    (1/6) failtest.1: FAIL (0.00 s)
    (2/6) sleeptest.1: PASS (1.00 s)
    (3/6) synctest.1: ERROR (0.01 s)
    (4/6) failtest.2: FAIL (0.00 s)
    (5/6) synctest.2: ERROR (0.01 s)
    (6/6) /tmp/script_that_passes.sh.1: PASS (0.02 s)
    PASS      : 2
    ERROR     : 2
    FAIL      : 2
    SKIP      : 0
    WARN      : 0
    INTERRUPT : 0
    TIME      : 1.04 s

Debugging tests
===============

When developing new tests, you frequently want to look at the straight
output of the job log in the stdout, without having to tail the job log.
In order to do that, you can use --show-job-log to the Avocado test runner::

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
involved functionalities for the Avocado runner will be discussed as
appropriate, during the introduction of important concepts.
