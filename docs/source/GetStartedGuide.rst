.. _get-started:

===============
Getting Started
===============

The first step towards using Avocado is, quite obviously, installing it.

Installing Avocado
==================

Avocado is available in RPM packages for Fedora, and `DEB packages for Ubuntu`_.

.. _DEB packages for Ubuntu: https://launchpad.net/~lmr/+archive/avocado

.. Note: the following text should instead reference the distro tiers levels

Avocado is primarily being developed on Fedora, but reasonable efforts
are being made to support other platforms such as Ubuntu.

Fedora
------

You can install the RPM packages by running the following commands::

    sudo curl https://repos-avocadoproject.rhcloud.com/static/avocado-fedora.repo -o /etc/yum.repos.d/avocado.repo
    sudo dnf install avocado

Enterprise Linux
----------------

If you're running either Red Hat Enterprise Linux or one of the derivatives
such as CentOS, just adapt to the following URL and commands::

    # If not already, enable epel (for RHEL7 it's following cmd)
    sudo yum install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
    # Add avocado repository and install avocado
    sudo curl https://repos-avocadoproject.rhcloud.com/static/avocado-el.repo -o /etc/yum.repos.d/avocado.repo
    sudo yum install avocado


Ubuntu
------

You can install Avocado by running the following commands::

    sudo echo "deb http://ppa.launchpad.net/lmr/avocado/ubuntu utopic main" >> /etc/apt/sources.list
    sudo apt-get update
    sudo apt-get install avocado

Generic installation from a GIT repository
------------------------------------------

First make sure you have a basic set of packages installed. The
following applies to Fedora based distributions, please adapt to
your platform::

    sudo yum install -y git gcc python-devel python-pip libvirt-devel libyaml-devel redhat-rpm-config xz-devel

Then to install Avocado from the git repository run::

    git clone git://github.com/avocado-framework/avocado.git
    cd avocado
    sudo make requirements
    sudo python setup.py install

Note that `python` and `pip` should point to the Python interpreter version 2.7.x.
If you're having trouble to install, you can try again and use the command line
utilities `python2.7` and `pip2.7`.

If you intend to hack on Avocado, you may want to look at :ref:`hacking-and-using`.

Using Avocado
=============

You should first experience Avocado by using the test runner, that is, the command
line tool that will conveniently run your tests and collect their results.

Running Tests
-------------

To do so, please run ``avocado`` with the ``run`` sub-command and the chosen test::

    $ avocado run /bin/true
    JOB ID    : 381b849a62784228d2fd208d929cc49f310412dc
    JOB LOG   : $HOME/avocado/job-results/job-2014-08-12T15.39-381b849a/job.log
    TESTS     : 1
     (1/1) /bin/true: PASS (0.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB HTML  : $HOME/avocado/job-results/job-2014-08-12T15.39-381b849a/html/results.html
    TIME : 0.01 s

You probably noticed that we used ``/bin/true`` as a test, and in accordance with our
expectations, it passed! These are known as `simple tests`, but there is also another
type of test, which we call `instrumented tests`. See more at :ref:`test-types` or just
keep reading.

Listing tests
-------------

You have two ways of discovering the tests. You can simulate the execution by
using the ``--dry-run`` argument::

    avocado run /bin/true --dry-run
    JOB ID     : 0000000000000000000000000000000000000000
    JOB LOG    : /tmp/avocado-dry-runSeWniM/job-2015-10-16T15.46-0000000/job.log
    TESTS      : 1
     (1/1) /bin/true: SKIP
    RESULTS    : PASS 0 | ERROR 0 | FAIL 0 | SKIP 1 | WARN 0 | INTERRUPT 0
    JOB HTML   : /tmp/avocado-dry-runSeWniM/job-2015-10-16T15.46-0000000/html/results.html
    TIME       : 0.00 s

which supports all ``run`` arguments, simulates the run and even lists the test params.

The other way is to use ``list`` subcommand that lists the discovered tests
If no arguments provided, Avocado lists "default" tests per each plugin.
The output might look like this::

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
    INSTRUMENTED /usr/share/avocado/tests/sleeptenmin.py
    INSTRUMENTED /usr/share/avocado/tests/sleeptest.py
    INSTRUMENTED /usr/share/avocado/tests/synctest.py
    INSTRUMENTED /usr/share/avocado/tests/timeouttest.py
    INSTRUMENTED /usr/share/avocado/tests/trinity.py
    INSTRUMENTED /usr/share/avocado/tests/warntest.py
    INSTRUMENTED /usr/share/avocado/tests/whiteboard.py

These Python files are considered by Avocado to contain ``INSTRUMENTED``
tests.

.. These should refer to proper simple tests example but they are currently
   lacking in our tree. See GitHub issue #628.

Let's now list a directory with a bunch of executable shell
scripts::

   $ avocado list /usr/share/avocado/simpletests/
   SIMPLE /usr/share/avocado/simpletests/failtest.sh
   SIMPLE /usr/share/avocado/simpletests/passtest.sh

Here, as mentioned before, ``SIMPLE`` means that those files are executables
treated as simple tests. You can also give the ``--verbose`` or ``-V`` flag to
display files that were found by Avocado, but are not considered Avocado tests::

    $ avocado list examples/gdb-prerun-scripts/ -V
    Type       file
    NOT_A_TEST examples/gdb-prerun-scripts/README
    NOT_A_TEST examples/gdb-prerun-scripts/pass-sigusr1

    SIMPLE: 0
    INSTRUMENTED: 0
    MISSING: 0
    NOT_A_TEST: 2

Notice that the verbose flag also adds summary information.

Writing a Simple Test
=====================

This very simple example of simple test written in shell script::

    $ echo '#!/bin/bash' > /tmp/simple_test.sh
    $ echo 'exit 0' >> /tmp/simple_test.sh
    $ chmod +x /tmp/simple_test.sh

Notice that the file is given executable permissions, which is a requirement for
Avocado to treat it as a simple test. Also notice that the script exits with status
code 0, which signals a successful result to Avocado.

Running A More Complex Test Job
===============================

You can run any number of test in an arbitrary order, as well as mix and match
instrumented and simple tests::

    $ avocado run failtest sleeptest synctest failtest synctest /tmp/simple_test.sh
    JOB ID    : 86911e49b5f2c36caeea41307cee4fecdcdfa121
    JOB LOG   : $HOME/avocado/job-results/job-2014-08-12T15.42-86911e49/job.log
    TESTS     : 6
     (1/6) failtest.1: FAIL (0.00 s)
     (2/6) sleeptest.1: PASS (1.00 s)
     (3/6) synctest.1: ERROR (0.01 s)
     (4/6) failtest.2: FAIL (0.00 s)
     (5/6) synctest.2: ERROR (0.01 s)
     (6/6) /tmp/simple_test.sh.1: PASS (0.02 s)
    RESULTS    : PASS 2 | ERROR 2 | FAIL 2 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB HTML  : $HOME/avocado/job-results/job-2014-08-12T15.42-86911e49/html/results.html
    TIME      : 1.04 s

.. _running-external-runner:

Running Tests With An External Runner
=====================================

It's quite common to have organically grown test suites in most
software projects. These usually include a custom built, very specific
test runner that knows how to find and run their own tests.

Still, running those tests inside Avocado may be a good idea for
various reasons, including being able to have results in different
human and machine readable formats, collecting system information
alongside those tests (the Avocado's `sysinfo` functionality), and
more.

Avocado makes that possible by means of its "external runner" feature. The
most basic way of using it is::

    $ avocado run --external-runner=/path/to/external_runner foo bar baz

In this example, Avocado will report individual test results for tests
`foo`, `bar` and `baz`. The actual results will be based on the return
code of individual executions of `/path/to/external_runner foo`,
`/path/to/external_runner bar` and finally `/path/to/external_runner baz`.

As another way to explain an show how this feature works, think of the
"external runner" as some kind of interpreter and the individual tests as
anything that this interpreter recognizes and is able to execute. A
UNIX shell, say `/bin/sh` could be considered an external runner, and
files with shell code could be considered tests::

    $ echo "exit 0" > /tmp/pass
    $ echo "exit 1" > /tmp/fail
    $ avocado run --external-runner=/bin/sh /tmp/pass /tmp/fail
    JOB ID     : 4a2a1d259690cc7b226e33facdde4f628ab30741
    JOB LOG    : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
    JOB HTML   : /home/<user>/avocado/job-results/job-<date>-<shortid>/html/results.html
    TESTS      : 2
    (1/2) /tmp/pass: PASS (0.01 s)
    (2/2) /tmp/fail: FAIL (0.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
    TIME       : 0.01 s

This example is pretty obvious, and could be achieved by giving
`/tmp/pass` and `/tmp/fail` shell "shebangs" (`#!/bin/sh`), making
them executable (`chmod +x /tmp/pass /tmp/fail)`, and running them as
"SIMPLE" tests.

But now consider the following example::

    $ avocado run --external-runner=/bin/curl http://local-avocado-server:9405/jobs/ \
                                           http://remote-avocado-server:9405/jobs/
    JOB ID     : 56016a1ffffaba02492fdbd5662ac0b958f51e11
    JOB LOG    : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
    JOB HTML   : /home/<user>/avocado/job-results/job-<date>-<shortid>/html/results.html
    TESTS      : 2
    (1/2) http://local-avocado-server:9405/jobs/: PASS (0.02 s)
    (2/2) http://remote-avocado-server:9405/jobs/: FAIL (3.02 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
    TIME       : 3.04 s

This effectively makes `/bin/curl` an "external test runner", responsible for
trying to fetch those URLs, and reporting PASS or FAIL for each of them.

Debugging tests
===============

When developing new tests, you frequently want to look straight at the
job log, without switching screens or having to "tail" the job log.

In order to do that, you can use ``--show-job-log`` option::

    $ avocado run examples/tests/sleeptest --show-job-log
    Job ID: f9ea1742134e5352dec82335af584d1f151d4b85

    START examples/tests/sleeptest.py

    PARAMS (key=timeout, path=*, default=None) => None
    PARAMS (key=sleep_length, path=*, default=1) => 1
    Sleeping for 1.00 seconds
    PASS examples/tests/sleeptest.py

    Test results available in $HOME/avocado/job-results/job-2015-06-02T10.45-f9ea174

As you can see, the UI output is suppressed and only the job log is shown,
making this a useful feature for test development and debugging.
