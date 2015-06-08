.. _reference-guide:

===============
Reference Guide
===============

This guide presents information on the Avocado basic design and its internals.

.. _job-id:

Job ID
======

The Job ID is a SHA1 string that has some information encoded:

* Hostname
* ISO timestamp
* 64 bit integer

The idea is to have a unique identifier that can be used for job data, for
the purposes of joining on a single database results obtained by jobs run
on different systems.

.. _test-types:

Test Types
==========

Avocado can natively run two different types of tests. You can mix and match those in a
single job.

Instrumented
------------

Tests written in Python that use the Avocado API. To consider a file to contain an instrumented
test, the Avocado test loader looks for an Avocado test class inside it.

This means that an executable written in Python is not always an instrumented test, but may work
as a simple test.

Simple
------

Any executable in your box. The criteria for PASS/FAIL is the return code of the executable.
If it returns 0, the test PASSes, if it returns anything else, it FAILs.
