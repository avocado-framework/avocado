Basic Concepts
==============

.. include:: /.include/helpus.rst

It is important to understand some basic concepts before start using Avocado.

Test Resolution
---------------

.. note:: Some definitions here may be out of date. The current runner can
   still be using some of these definitions in its design, however, we are
   working on an improved version of the runner, the NextRunner that will use
   an alternative strategy.

When you use the Avocado runner, frequently you'll provide paths to files,
that will be inspected, and acted upon depending on their contents. The
diagram below shows how Avocado analyzes a file and decides what to do with
it:

.. figure:: /_static/diagram.png

It's important to note that the inspection mechanism is safe (that is, Python
classes and files are not actually loaded and executed on discovery and
inspection stage). Due to the fact Avocado doesn't actually load the code and
classes, the introspection is simple and will *not* catch things like buggy
test modules, missing imports and miscellaneous bugs in the code you want to
list or run. We recommend only running tests from sources you trust, use of
static checking and reviews in your test development process.

Due to the simple test inspection mechanism, Avocado will not recognize test
classes that inherit from a class derived from :class:`avocado.Test`. Please
refer to the `WritingTests` documentation on how to use the tags functionality
to mark derived classes as Avocado test classes.

Identifiers and references
--------------------------

Job ID
~~~~~~

The Job ID is a random SHA1 string that uniquely identifies a given job.

The full form of the SHA1 string is used is most references to a job::

  $ avocado run sleeptest.py
  JOB ID     : 49ec339a6cca73397be21866453985f88713ac34
  ...

But a shorter version is also used at some places, such as in the job results
location::

  JOB LOG    : $HOME/avocado/job-results/job-2015-06-10T10.44-49ec339/job.log


Test References
~~~~~~~~~~~~~~~

.. warning:: TODO: We are talking here about Test Resolver, but the reader was
  not introduced to this concept yet.

A Test Reference is a string that can be resolved into
(interpreted as) one or more tests by the Avocado Test Resolver.
A given resolver plugin is free to interpret a test reference,
it is completely abstract to the other components of Avocado.

When the test references are about Instrumented Tests, Avocado will find any
Instrumented test that **starts** with the reference, like a "wildcard". For
instance::

  $ avocado run ./test.py:MyTest:test_foo

This command will resolve all tests (methods) that starts with `test_foo`. For
more information about this type of tests, please visit the :ref:`Instrumented`
section of this document.

.. note:: Mapping the Test References to tests can be affected
   by command-line switches like `--external-runner`, which
   completelly changes the meaning of the given strings.

Conventions
~~~~~~~~~~~

Even though each resolver implementation is free to interpret a
reference string as it sees fit, it's a good idea to set common user
expectations.

It's common for a single file to contain multiple tests.  In that
case, information about the specific test to reference can be added
after the filesystem location and a colon, that is, for the
reference::

  passtest.py:PassTest.test

Unless a file with that exact name exists, most resolvers will split
it into `passtest.py` as the filesystem path, and `PassTest.test` as
an additional specification for the individual test.  It's also
possible that some resolvers will support regular expressions and
globs for the additional information component.

Test Name
~~~~~~~~~

A test name is an arbitrarily long string that unambiguously points to the
source of a single test. In other words the Avocado Test Resolver, as
configured for a particular job, should return one and only one test as the
interpretation of this name.

This name can be as specific as necessary to make it unique.  Therefore it can
contain an arbitrary number of variables, prefixes, suffixes, tags, etc.  It
all depends on user preferences, what is supported by Avocado via its Test
Resolvers and the context of the job.

The output of the Test Resolver when resolving Test References should always be
a list of unambiguous Test Names (for that particular job).

Notice that although the Test Name has to be unique, one test can be run more
than once inside a job.

By definition, a Test Name is a Test Reference, but the reciprocal is not
necessarily true, as the latter can represent more than one test.

Examples of Test Names::

   '/bin/true'
   'passtest.py:Passtest.test'
   'file:///tmp/passtest.py:Passtest.test'
   'multiple_tests.py:MultipleTests.test_hello'
   'type_specific.io-github-autotest-qemu.systemtap_tracing.qemu.qemu_free'


Variant IDs
~~~~~~~~~~~

The varianter component creates different sets of variables (known as
"variants"), to allow tests to be run individually in each of them.

A Variant ID is an arbitrary and abstract string created by the varianter
plugin to identify each variant. It should be unique per variant inside a set.
In other words, the varianter plugin generates a set of variants, identified by
unique IDs.

A simpler implementation of the varianter uses serial integers as Variant IDs.
A more sophisticated implementation could generate Variant IDs with more
semantic, potentially representing their contents.


Test ID
~~~~~~~

A test ID is a string that uniquely identifies a test in the context of a job.
When considering a single job, there are no two tests with the same ID.

A test ID should encapsulate the Test Name and the Variant ID, to allow direct
identification of a test. In other words, by looking at the test ID it should
be possible to identify:

  - What's the test name
  - What's the variant used to run this test (if any)

Test IDs don't necessarily keep their uniqueness properties when considered
outside of a particular job, but two identical jobs run in the exact same
environment should generate a identical sets of Test IDs.

Syntax::

   <unique-id>-<test-name>[;<variant-id>]

Example of Test IDs::

   '1-/bin/true'
   '2-passtest.py:Passtest.test;quiet-'
   '3-file:///tmp/passtest.py:Passtest.test'
   '4-multiple_tests.py:MultipleTests.test_hello;maximum_debug-df2f'
   '5-type_specific.io-github-autotest-qemu.systemtap_tracing.qemu.qemu_free'

.. _test-types:

Test types
----------

Avocado at its simplest configuration can run three different types of tests
[#f1]_. You can mix and match those in a single job.

Simple
~~~~~~

Any executable in your box. The criteria for PASS/FAIL is the return code of the executable.
If it returns 0, the test PASSes, if it returns anything else, it FAILs.

Python unittest
~~~~~~~~~~~~~~~

The discovery of classical Python unittest is also supported, although unlike
Python unittest we still use static analysis to get individual tests so
dynamically created cases are not recognized. Also note that test result SKIP
is reported as CANCEL in Avocado as SKIP test meaning differs from our
definition. Apart from that there should be no surprises when running unittests
via Avocado.

.. _Instrumented:

Instrumented
~~~~~~~~~~~~

These are tests written in Python or BASH with the Avocado helpers that use the
Avocado test API.

To be more precise, the Python file must contain a class derived from
:mod:`avocado.test.Test`.  This means that an executable written in Python is
not always an instrumented test, but may work as a simple test.

The instrumented tests allows the writer finer control over the process
including logging, test result status and other more sophisticated test APIs.

Test statuses ``PASS``, ``WARN`` and ``SKIP`` are considered
successful. The ``ERROR``, ``FAIL`` and ``INTERRUPTED`` signal failures.

TAP
~~~

TAP tests are pretty much like Simple tests in the sense tha they are
programs (either binaries or scripts) that will executed.  The
difference is that the test result will be decided based on the
produced output, that should be in `Test Anything Protocol
<https://testanything.org>`_ format.

Test statuses
-------------

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

Exit codes
----------

Avocado exit code tries to represent different things that can happen during an
execution. That means exit codes can be a combination of codes that were ORed
together as a single exit code. The final exit code can be de-bundled so users
can have a good idea on what happened to the job.

The single individual exit codes are:

* AVOCADO_ALL_OK (0)
* AVOCADO_TESTS_FAIL (1)
* AVOCADO_JOB_FAIL (2)
* AVOCADO_FAIL (4)
* AVOCADO_JOB_INTERRUPTED (8)

If a job finishes with exit code `9`, for example, it means we had at least one
test that failed and also we had at some point a job interruption, probably due
to the job timeout or a `CTRL+C`.

.. [#f1] Avocado plugins can introduce additional test types.
