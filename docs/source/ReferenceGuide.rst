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

These are tests written in Python that use the Avocado test API.

To be more precise, the Python file must contain a class derived from :mod:`avocado.test.Test`.
This means that an executable written in Python is not always an instrumented test, but may work
as a simple test.

By the way, the term instrumented is used because the Avocado Python test classes allow you to
get more features for your test, such as logging facilities and more sophisticated test APIs.

Simple
------

Any executable in your box. The criteria for PASS/FAIL is the return code of the executable.
If it returns 0, the test PASSes, if it returns anything else, it FAILs.

Test Resolution
===============

When you use the Avocado runner, frequently you'll provide paths to files,
that will be inspected, and acted upon depending on their contents. The
diagram below shows how Avocado analyzes a file and decides what to do with
it:

.. figure:: diagram.png
