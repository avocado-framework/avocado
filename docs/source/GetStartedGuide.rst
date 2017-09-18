.. _get-started:

===============
Getting Started
===============

The first step towards using Avocado is, quite obviously, installing it.

.. Note: this section section shares content with the project README
         file.  When editing this section, also sync the content with
         the README file.  Also notice that this file uses a larger
         set of ReST/sphinx statements, which do not look as good on a
         plain README file.

.. _Installing Avocado:

Installing Avocado
==================

Installing from Packages
------------------------

Fedora
~~~~~~

Avocado is available in stock Fedora 24 and later.  The main package
name is ``python-avocado``, and can be installed with::

    dnf install python-avocado

Other available packages (depending on the Avocado version) may include:

* ``python-avocado-examples``: contains example tests and other example files
* ``python2-avocado-plugins-output-html``: HTML job report plugin
* ``python2-avocado-plugins-resultsdb``: propagate Job results to Resultsdb
* ``python2-avocado-plugins-runner-remote``: execution of jobs on a remote machine
* ``python2-avocado-plugins-runner-vm``: execution of jobs on a libvirt based VM
* ``python2-avocado-plugins-runner-docker``: execution of jobs on a Docker container
* ``python-avocado-plugins-varianter-yaml-to-mux``: parse YAML file into variants

.. _fedora-from-avocados-own-repo:

Fedora from Avocado's own Repo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Avocado project also makes the latest release, and the LTS (Long
Term Stability) releases available from its own package repository.
To use it, first get the package repositories configuration file by
running the following command::

    sudo curl https://repos-avocadoproject.rhcloud.com/static/avocado-fedora.repo -o /etc/yum.repos.d/avocado.repo

Now check if you have the ``avocado`` and ``avocado-lts`` repositories configured by running::

    sudo dnf repolist avocado avocado-lts
    ...
    repo id      repo name                          status
    avocado      Avocado                            50
    avocado-lts  Avocado LTS (Long Term Stability)  disabled

Regular users of Avocado will want to use the standard ``avocado``
repository, which tracks the latest Avocado releases.  For more
information about the LTS releases, please refer to
:ref:`rfc-long-term-stability`  and to your package management
docs on how to switch to the ``avocado-lts`` repo.

Finally, after deciding between regular Avocado releases or LTS, you
can install the RPM packages by running the following commands::

    dnf install python-avocado

Additionally, other Avocado packages are available for Fedora:

* ``python-avocado-examples``: contains example tests and other example files
* ``python2-avocado-plugins-output-html``: HTML job report plugin
* ``python2-avocado-plugins-resultsdb``: propagate Job results to Resultsdb
* ``python2-avocado-plugins-runner-remote``: execution of jobs on a remote machine
* ``python2-avocado-plugins-runner-vm``: execution of jobs on a libvirt based VM
* ``python2-avocado-plugins-runner-docker``: execution of jobs on a Docker container
* ``python-avocado-plugins-varianter-yaml-to-mux``: parse YAML file into variants

Enterprise Linux
~~~~~~~~~~~~~~~~

Avocado packages for Enterprise Linux are available from the Avocado
project RPM repository.  Additionally, some packages from the EPEL repo are
necessary, so you need to enable it first.  For EL7, running the
following command should do it::

    yum install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

Then you must use the Avocado project RHEL repo
(https://repos-avocadoproject.rhcloud.com/static/avocado-el.repo).
Running the following command should give you the basic Avocado
installation ready::

    curl https://repos-avocadoproject.rhcloud.com/static/avocado-el.repo -o /etc/yum.repos.d/avocado.repo
    yum install python-avocado

Other available packages (depending on the Avocado version) may include:

* ``python-avocado-examples``: contains example tests and other example files
* ``python2-avocado-plugins-output-html``: HTML job report plugin
* ``python2-avocado-plugins-resultsdb``: propagate Job results to Resultsdb
* ``python2-avocado-plugins-runner-remote``: execution of jobs on a remote machine
* ``python2-avocado-plugins-runner-vm``: execution of jobs on a libvirt based VM
* ``python2-avocado-plugins-runner-docker``: execution of jobs on a Docker container
* ``python-avocado-plugins-varianter-yaml-to-mux``: parse YAML file into variants

The LTS (Long Term Stability) repositories are also available for
Enterprise Linux.  Please refer to :ref:`rfc-long-term-stability` and
to your package management docs on how to switch to the
``avocado-lts`` repo.

OpenSUSE
~~~~~~~~

The `OpenSUSE`_ project packages LTS versions of Avocado.  You can
install packages by running the following commands::

  sudo zypper install avocado

Debian
~~~~~~

DEB package support is available in the source tree (look at the
``contrib/packages/debian`` directory.  No actual packages are
provided by the Avocado project or the Debian repos.

Generic installation from a GIT repository
------------------------------------------

First make sure you have a basic set of packages installed. The
following applies to Fedora based distributions, please adapt to
your platform::

    sudo dnf install -y python2 git gcc python-devel python-pip libvirt-devel libffi-devel openssl-devel libyaml-devel redhat-rpm-config xz-devel

Then to install Avocado from the git repository run::

    git clone git://github.com/avocado-framework/avocado.git
    cd avocado
    sudo make requirements
    sudo python setup.py install

Note that `python` and `pip` should point to the Python interpreter version 2.7.x.
If you're having trouble to install, you can try again and use the command line
utilities `python2.7` and `pip2.7`.

Please note that some Avocado functionality may be implemented by
optional plugins.  To install say, the HTML report plugin, run::

    cd optional_plugins/html
    sudo python setup.py install

If you intend to hack on Avocado, you may want to look at :ref:`hacking-and-using`.

Installing from standard Python tools
-------------------------------------

Avocado can also be installed by the standard Python packaging tools,
namely ``pip``.  On most POSIX systems with Python >= 2.7 and ``pip``
available, installation can be performed with the following commands::

  pip install avocado-framework

.. note:: As a design decision, only the dependencies for the core
          Avocado test runner will be installed.  You may notice,
          depending on your system, that some plugins will fail to load,
          due to those missing dependencies.

If you want to install all the requirements for all plugins, you may
attempt to do so by running::

  pip install -r https://raw.githubusercontent.com/avocado-framework/avocado/master/requirements.txt

which installs the python dependencies, although you might still be
missing the non-python dependencies so the use of distribution package
is preferred.

The optional plugins are also shipped via PyPI and you should be able
to find them via ``pip search avocado-framework``. Some of them
are listed below:

* `avocado-framework-plugin-result-html <https://pypi.python.org/pypi/avocado-framework-plugin-result-html>`_: HTML Report for Jobs
* `avocado-framework-plugin-resultsdb <https://pypi.python.org/pypi/avocado-framework-plugin-resultsdb>`_: Propagate Job results to Resultsdb
* `avocado-framework-plugin-runner-remote <https://pypi.python.org/pypi/avocado-framework-plugin-runner-remote>`_: Runner for Remote Execution
* `avocado-framework-plugin-runner-vm <https://pypi.python.org/pypi/avocado-framework-plugin-runner-vm>`_: Runner for libvirt VM Execution
* `avocado-framework-plugin-runner-docker <https://pypi.python.org/pypi/avocado-framework-plugin-runner-docker>`_: Runner for Execution on Docker Containers
* `avocado-framework-plugin-loader-yaml <https://pypi.python.org/pypi/avocado-framework-plugin-loader-yaml>`_: Loads tests from YAML files
* `avocado-framework-plugin-robot <https://pypi.python.org/pypi/avocado-framework-plugin-robot>`_: Execution of Robot Framework tests
* `avocado-framework-plugin-varianter-yaml-to-mux <https://pypi.python.org/pypi/avocado-framework-plugin-varianter-yaml-to-mux>`_: Parse YAML file into variants

Using Avocado
=============

You should first experience Avocado by using the test runner, that is, the command
line tool that will conveniently run your tests and collect their results.

Running Tests
-------------

To do so, please run ``avocado`` with the ``run`` sub-command followed by
a test reference, which could be either a path to the file, or a
recognizable name::

    $ avocado run /bin/true
    JOB ID    : 381b849a62784228d2fd208d929cc49f310412dc
    JOB LOG   : $HOME/avocado/job-results/job-2014-08-12T15.39-381b849a/job.log
     (1/1) /bin/true: PASS (0.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB TIME   : 0.11 s
    JOB HTML  : $HOME/avocado/job-results/job-2014-08-12T15.39-381b849a/html/results.html

You probably noticed that we used ``/bin/true`` as a test, and in accordance with our
expectations, it passed! These are known as `simple tests`, but there is also another
type of test, which we call `instrumented tests`. See more at :ref:`test-types` or just
keep reading.

.. note:: Although in most cases running ``avocado run $test1 $test3 ...`` is
          fine, it can lead to argument vs. test name clashes. The safest
          way to execute tests is ``avocado run --$argument1 --$argument2
          -- $test1 $test2``. Everything after `--` will be considered
          positional arguments, therefore test names (in case of
          ``avocado run``)

Listing tests
-------------

You have two ways of discovering the tests. You can simulate the execution by
using the ``--dry-run`` argument::

    avocado run /bin/true --dry-run
    JOB ID     : 0000000000000000000000000000000000000000
    JOB LOG    : /tmp/avocado-dry-runSeWniM/job-2015-10-16T15.46-0000000/job.log
     (1/1) /bin/true: SKIP
    RESULTS    : PASS 0 | ERROR 0 | FAIL 0 | SKIP 1 | WARN 0 | INTERRUPT 0
    JOB TIME   : 0.10 s
    JOB HTML   : /tmp/avocado-dry-runSeWniM/job-2015-10-16T15.46-0000000/html/results.html

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
    ...

These Python files are considered by Avocado to contain ``INSTRUMENTED``
tests.

Let's now list only the executable shell scripts::

    $ avocado list | grep ^SIMPLE
    SIMPLE       /usr/share/avocado/tests/env_variables.sh
    SIMPLE       /usr/share/avocado/tests/output_check.sh
    SIMPLE       /usr/share/avocado/tests/simplewarning.sh
    SIMPLE       /usr/share/avocado/tests/failtest.sh
    SIMPLE       /usr/share/avocado/tests/passtest.sh

Here, as mentioned before, ``SIMPLE`` means that those files are executables
treated as simple tests. You can also give the ``--verbose`` or ``-V`` flag to
display files that were found by Avocado, but are not considered Avocado tests::

    $ avocado list examples/gdb-prerun-scripts/ -V
    Type       Test                                     Tag(s)
    NOT_A_TEST examples/gdb-prerun-scripts/README
    NOT_A_TEST examples/gdb-prerun-scripts/pass-sigusr1

    TEST TYPES SUMMARY
    ==================
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

    $ avocado run failtest.py sleeptest.py synctest.py failtest.py synctest.py /tmp/simple_test.sh
    JOB ID    : 86911e49b5f2c36caeea41307cee4fecdcdfa121
    JOB LOG   : $HOME/avocado/job-results/job-2014-08-12T15.42-86911e49/job.log
     (1/6) failtest.py:FailTest.test: FAIL (0.00 s)
     (2/6) sleeptest.py:SleepTest.test: PASS (1.00 s)
     (3/6) synctest.py:SyncTest.test: PASS (2.43 s)
     (4/6) failtest.py:FailTest.test: FAIL (0.00 s)
     (5/6) synctest.py:SyncTest.test: PASS (2.44 s)
     (6/6) /tmp/simple_test.sh.1: PASS (0.02 s)
    RESULTS    : PASS 4 | ERROR 0 | FAIL 2 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB TIME   : 5.98 s
    JOB HTML  : $HOME/avocado/job-results/job-2014-08-12T15.42-86911e49/html/results.html

Interrupting The Job On First Failed Test (failfast)
====================================================

The Avocado ``run`` command has the option ``--failfast on`` to exit the job
on first failed test::

    $ avocado run --failfast on /bin/true /bin/false /bin/true /bin/true
    JOB ID     : eaf51b8c7d6be966bdf5562c9611b1ec2db3f68a
    JOB LOG    : $HOME/avocado/job-results/job-2016-07-19T09.43-eaf51b8/job.log
     (1/4) /bin/true: PASS (0.01 s)
     (2/4) /bin/false: FAIL (0.01 s)
    Interrupting job (failfast).
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 2 | WARN 0 | INTERRUPT 0
    JOB TIME   : 0.12 s
    JOB HTML   : /home/apahim/avocado/job-results/job-2016-07-19T09.43-eaf51b8/html/results.html

The ``--failfast`` option accepts the argument ``off``. Since it's disabled
by default, the ``off`` argument only makes sense in replay jobs, when the
original job was executed with ``--failfast on``.

Ignoring Missing Test References
================================

When you provide a list of test references, Avocado will try to resolve
all of them to tests. If one or more test references can not be resolved
to tests, the Job will not be created. Example::

    $ avocado run passtest.py badtest.py
    Unable to resolve reference(s) 'badtest.py' with plugins(s) 'file', 'robot', 'external', try running 'avocado list -V badtest.py' to see the details.

But if you want to execute the Job anyway, with the tests that could be
resolved, you can use ``--ignore-missing-references on``. The same message
will appear in the UI, but the Job will be executed::

    $ avocado run passtest.py badtest.py --ignore-missing-references on
    Unable to resolve reference(s) 'badtest.py' with plugins(s) 'file', 'robot', 'external', try running 'avocado list -V badtest.py' to see the details.
    JOB ID     : 85927c113074b9defd64ea595d6d1c3fdfc1f58f
    JOB LOG    : $HOME/avocado/job-results/job-2017-05-17T10.54-85927c1/job.log
     (1/1) passtest.py:PassTest.test: PASS (0.02 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 0.11 s
    JOB HTML   : $HOME/avocado/job-results/job-2017-05-17T10.54-85927c1/html/results.html

The ``--ignore-missing-references`` option accepts the argument ``off``.
Since it's disabled by default, the ``off`` argument only makes sense in
replay jobs, when the original job was executed with
``--ignore-missing-references on``.

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
    (1/2) /tmp/pass: PASS (0.01 s)
    (2/2) /tmp/fail: FAIL (0.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB TIME   : 0.11 s
    JOB HTML   : /home/<user>/avocado/job-results/job-<date>-<shortid>/html/results.html

This example is pretty obvious, and could be achieved by giving
`/tmp/pass` and `/tmp/fail` shell "shebangs" (`#!/bin/sh`), making
them executable (`chmod +x /tmp/pass /tmp/fail)`, and running them as
"SIMPLE" tests.

But now consider the following example::

    $ avocado run --external-runner=/bin/curl http://local-avocado-server:9405/jobs/ \
                                           http://remote-avocado-server:9405/jobs/
    JOB ID     : 56016a1ffffaba02492fdbd5662ac0b958f51e11
    JOB LOG    : /home/<user>/avocado/job-results/job-<date>-<shortid>/job.log
    (1/2) http://local-avocado-server:9405/jobs/: PASS (0.02 s)
    (2/2) http://remote-avocado-server:9405/jobs/: FAIL (3.02 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB TIME   : 3.14 s
    JOB HTML   : /home/<user>/avocado/job-results/job-<date>-<shortid>/html/results.html

This effectively makes `/bin/curl` an "external test runner", responsible for
trying to fetch those URLs, and reporting PASS or FAIL for each of them.

Debugging tests
===============

Showing test output
-------------------

When developing new tests, you frequently want to look straight at the
job log, without switching screens or having to "tail" the job log.

In order to do that, you can use ``avocado --show test run ...`` or
``avocado run --show-job-log ...`` options::

    $ avocado --show test run examples/tests/sleeptest.py
    ...
    Job ID: f9ea1742134e5352dec82335af584d1f151d4b85

    START 1-sleeptest.py:SleepTest.test

    PARAMS (key=timeout, path=*, default=None) => None
    PARAMS (key=sleep_length, path=*, default=1) => 1
    Sleeping for 1.00 seconds
    PASS 1-sleeptest.py:SleepTest.test

    Test results available in $HOME/avocado/job-results/job-2015-06-02T10.45-f9ea174

As you can see, the UI output is suppressed and only the job log is shown,
making this a useful feature for test development and debugging.

Interrupting tests execution
----------------------------

To interrupt a job execution a user can press ``ctrl+c`` which after a single
press sends SIGTERM to the main test's process and waits for it to finish.
If this does not help user can press ``ctrl+c`` again (after 2s grace period)
which destroys the test's process ungracefully and safely finishes the job
execution always providing the test results.

To pause the test execution a user can use ``ctrl+z`` which sends ``SIGSTOP``
to all processes inherited from the test's PID. We do our best to stop all
processes, but the operation is not atomic and some new processes might
not be stopped. Another ``ctrl+z`` sends ``SIGCONT`` to all
processes inherited by the test's PID resuming the execution. Note the
test execution time (concerning the test timeout) are still running while
the test's process is stopped.

The test can also be interrupted by an Avocado feature. One example would
be the `Debugging with GDB` :doc:`DebuggingWithGDB` feature.

For custom interactions it is also possible to use other means like ``pdb``
or ``pydevd`` :doc:`DevelopmentTips` breakpoints. Beware it's not possible
to use ``STDIN`` from tests (unless dark magic is used).

.. _OpenSUSE: https://build.opensuse.org/package/show/Virtualization:Tests/avocado
