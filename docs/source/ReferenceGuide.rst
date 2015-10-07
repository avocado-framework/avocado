.. _reference-guide:

===============
Reference Guide
===============

This guide presents information on the Avocado basic design and its internals.

.. _job-id:

Job ID
======

The Job ID is a random SHA1 string that uniquely identifies a given job.

The full form of the SHA1 string is used is most references to a job::

  $ avocado run sleeptest
  JOB ID     : 49ec339a6cca73397be21866453985f88713ac34
  ...

But a shorter version is also used at some places, such as in the job
results location::

  JOB LOG    : $HOME/avocado/job-results/job-2015-06-10T10.44-49ec339/job.log

.. _test-types:

Test Types
==========

Avocado at its simplest configuration can run two different types of tests [#f1]_. You can mix
and match those in a single job.

Instrumented
------------

These are tests written in Python or BASH with the Avocado helpers that use the Avocado test API.

To be more precise, the Python file must contain a class derived from :mod:`avocado.test.Test`.
This means that an executable written in Python is not always an instrumented test, but may work
as a simple test.

The instrumented tests allows the writer finer control over the process
including logging, test result status and other more sophisticated test APIs.

Test statuses ``PASS``, ``WARN``, ``START`` and ``TEST_NA`` are considered as
successful builds. The ``ABORT``, ``ERROR``, ``FAIL``, ``ALERT``, ``RUNNING``,
``NOSTATUS`` and ``INTERRUPTED`` are considered as failed ones.

Simple
------

Any executable in your box. The criteria for PASS/FAIL is the return code of the executable.
If it returns 0, the test PASSes, if it returns anything else, it FAILs.

Test Statuses
=============

Avocado sticks to the following definitions of test statuses:

 * ```PASS```: The test passed, which means all conditions being tested have passed.
 * ```FAIL```: The test failed, which means at least one condition being tested has
   failed. Ideally, it should mean a problem in the software being tested has been found.
 * ```ERROR```: An error happened during the test execution. This can happen, for example,
   if there's a bug in the test runner, in its libraries or if a resource breaks unexpectedly.
   Uncaught exceptions in the test code will also result in this status.
 * ```SKIP```: The test runner decided a requested test should not be run. This
   can happen, for example, due to missing requirements in the test environment
   or when there's a job timeout.

.. _libraries-apis:

Libraries and APIs
==================

The Avocado libraries and its APIs are a big part of what Avocado is.

But, to avoid having any issues you should understand what parts of the Avocado
libraries are intended for test writers and their respective API stability promises.

Test APIs
---------

At the most basic level there's the Test APIs which you should use when writing
tests in Python and planning to make use of any other utility library.

The Test APIs can be found in the :mod:`avocado` main module, and its most important
member is the :class:`avocado.Test` class. By conforming to the :class:`avocado.Test`
API, that is, by inheriting from it, you can use the full set of utility libraries.

The Test APIs are guaranteed to be stable across a single major version of Avocado.
That means that a test written for a given version of Avocado should not break on later
minor versions because of Test API changes.

Utility Libraries
-----------------

There are also a large number of utility libraries that can be found under the
:mod:`avocado.utils` namespace. These are very general in nature and can help you
speed up your test development.

The utility libraries may receive incompatible changes across minor versions, but
these will be done in a staged fashion. If a given change to an utility library
can cause test breakage, it will first be documented and/or deprecated, and only
on the next subsequent minor version it will actually be changed.

What this means is that upon updating to later minor versions of Avocado, you
should look at the Avocado Release Notes for changes that may impact your tests.

Core (Application) Libraries
----------------------------

Finally, everything under :mod:`avocado.core` is part of the application's
infrastructure and should not be used by tests.

Extensions and Plugins can use the core libraries, but API stability is not
guaranteed at any level.

Test Resolution
===============

When you use the Avocado runner, frequently you'll provide paths to files,
that will be inspected, and acted upon depending on their contents. The
diagram below shows how Avocado analyzes a file and decides what to do with
it:

.. figure:: diagram.png

It's important to note that the inspection mechanism is safe (that is, python
classes and files are not actually loaded and executed on discovery and
inspection stage). Due to the fact Avocado doesn't actually load the code
and classes, the introspection is simple and will *not* catch things like
buggy test modules, missing imports and miscellaneous bugs in the code you
want to list or run. We recommend only running tests from sources you trust,
use of static checking and reviews in your test development process.

Due to the simple test inspection mechanism, avocado will not recognize test
classes that inherit from a class derived from :class:`avocado.Test`. Please
refer to the :doc:`WritingTests` documentation on how to use the tags functionality
to mark derived classes as avocado test classes.

Results Specification
=====================

On a machine that executed tests, job results are available under
``[job-results]/job-[timestamp]-[short job ID]``, where ``logdir`` is the configured Avocado
logs directory (see the data dir plugin), and the directory name includes
a timestamp, such as ``job-2014-08-12T15.44-565e8de``. A typical
results directory structure can be seen below ::

    $HOME/avocado/job-results/job-2014-08-13T00.45-4a92bc0/
    ├── id
    ├── job.log
    ├── results.json
    ├── results.xml
    ├── sysinfo
    │   ├── post
    │   │   ├── brctl_show
    │   │   ├── cmdline
    │   │   ├── cpuinfo
    │   │   ├── current_clocksource
    │   │   ├── df_-mP
    │   │   ├── dmesg_-c
    │   │   ├── dmidecode
    │   │   ├── fdisk_-l
    │   │   ├── gcc_--version
    │   │   ├── hostname
    │   │   ├── ifconfig_-a
    │   │   ├── interrupts
    │   │   ├── ip_link
    │   │   ├── ld_--version
    │   │   ├── lscpu
    │   │   ├── lspci_-vvnn
    │   │   ├── meminfo
    │   │   ├── modules
    │   │   ├── mount
    │   │   ├── mounts
    │   │   ├── numactl_--hardware_show
    │   │   ├── partitions
    │   │   ├── scaling_governor
    │   │   ├── uname_-a
    │   │   ├── uptime
    │   │   └── version
    │   └── pre
    │       ├── brctl_show
    │       ├── cmdline
    │       ├── cpuinfo
    │       ├── current_clocksource
    │       ├── df_-mP
    │       ├── dmesg_-c
    │       ├── dmidecode
    │       ├── fdisk_-l
    │       ├── gcc_--version
    │       ├── hostname
    │       ├── ifconfig_-a
    │       ├── interrupts
    │       ├── ip_link
    │       ├── ld_--version
    │       ├── lscpu
    │       ├── lspci_-vvnn
    │       ├── meminfo
    │       ├── modules
    │       ├── mount
    │       ├── mounts
    │       ├── numactl_--hardware_show
    │       ├── partitions
    │       ├── scaling_governor
    │       ├── uname_-a
    │       ├── uptime
    │       └── version
    └── test-results
        └── tests
            ├── sleeptest.py.long
            │   ├── data
            │   ├── debug.log
            │   └── sysinfo
            │       ├── post
            │       └── pre
            ├── sleeptest.py.medium
            │   ├── data
            │   ├── debug.log
            │   └── sysinfo
            │       ├── post
            │       └── pre
            └── sleeptest.py.short
                ├── data
                ├── debug.log
                └── sysinfo
                    ├── post
                    └── pre
    
    20 directories, 59 files


From what you can see, the results dir has:

1) A human readable ``id`` in the top level, with the job SHA1.
2) A human readable ``job.log`` in the top level, with human readable logs of
   the task
3) A machine readable ``results.xml`` in the top level, with a summary of the
   job information in xUnit format.
4) A top level ``sysinfo`` dir, with sub directories ``pre`` and ``post``, that store
   sysinfo files pre job and post job, respectively.
5) Subdirectory ``test-results``, that contains a number of subdirectories
   (tagged testnames). Those tagged testnames represent instances of test
   execution results.

Test execution instances specification
--------------------------------------

The instances should have:

1) A top level human readable ``test.log``, with test debug information
2) A ``sysinfo`` subdir, with sub directories ``pre`` and ``post``, that store
   sysinfo files pre test and post test, respectively.
3) A ``data`` subdir, where the test can output a number of files if necessary.

.. [#f1] Avocado plugins can introduce additional test types.
