Basic Concepts
==============

It is important to understand some basic concepts before start using Avocado.


Identifiers and references
--------------------------

Job ID
~~~~~~

The Job ID is a random SHA1 string that uniquely identifies a given job.

The full form of the SHA1 string is used is most references to a job::

  $ avocado run examples/tests/sleeptest.py
  JOB ID     : 49ec339a6cca73397be21866453985f88713ac34
  ...

But a shorter version is also used at some places, such as in the job results
location::

  JOB LOG    : $HOME/avocado/job-results/job-2015-06-10T10.44-49ec339/job.log


Test Resolver
~~~~~~~~~~~~~

A test resolver is Avocado's component that will take a reference you
know about and will turn it into an actual test that can be run.  This
reference, explained next, can be pretty much any string, but it'll
usually be some form of text containing the path to the file that
contains the test.

For more information please refer to :ref:`finding_tests`.

Test References
~~~~~~~~~~~~~~~

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
it into ``passtest.py`` as the filesystem path, and ``PassTest.test`` as
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

Avocado at its simplest configuration can run three different types of tests:

* Executable tests (``exec-test``)
* Python unittest tests (``python-unittest``)
* Avocado Instrumented tests (``avocado-instrumented``)
* TAP producing tests (``tap``)

You can mix and match those in a single job.

Avocado plugins can also introduce additional test types.

Executable tests
~~~~~~~~~~~~~~~~

Any executable file can serve as a test. The criteria for PASS/FAIL is
the return code of the executable.  If it returns 0, the test PASSes,
if it returns anything else, it FAILs.

Python unittest tests
~~~~~~~~~~~~~~~~~~~~~

The discovery of classical Python unittest is also supported, although unlike
Python unittest we still use static analysis to get individual tests so
dynamically created cases are not recognized. Apart from that there should be
no surprises when running unittests via Avocado.

.. _Instrumented:

Avocado Instrumented tests
~~~~~~~~~~~~~~~~~~~~~~~~~~

These are tests written in Python or BASH with the Avocado helpers that use the
Avocado test API.

To be more precise, the Python file must contain a class derived from
:mod:`avocado.test.Test`.  This means that an executable written in Python is
not always an instrumented test, but may work as an executable test.

The instrumented tests allows the writer finer control over the process
including logging, test result status and other more sophisticated test APIs.

Test statuses ``PASS``, ``WARN`` and ``SKIP`` are considered
successful. The ``ERROR``, ``FAIL`` and ``INTERRUPTED`` signal failures.

TAP producing tests
~~~~~~~~~~~~~~~~~~~

TAP tests are pretty much like executable tests in the sense that they are
programs (either binaries or scripts) that will executed.  The
difference is that the test result will be decided based on the
produced output, that should be in `Test Anything Protocol
<https://testanything.org>`_ format.

Even though such executable can be seen as test suite from avocado point of view,
it will be considered as one standalone test. If you want to get result of each
test of such executable, you can get generated tap output in debug.log file.
:ref:`avocado-log-files`

.. note::
  The result of Tap test is based on the importance of individual results types
  like this:

  `SKIP -> PASS -> FAIL`.  

  This means if one of the tests in TAP output
  is `not ok` the TAP test result is `FAIL`. If all tests are `ok` or `skip`
  the results is `PASS` and if all results are `skip` the result is `SKIP`.

Test statuses
-------------

Avocado sticks to the following definitions of test statuses:

 * ``PASS``: The test passed, which means all conditions being tested have passed.
 * ``FAIL``: The test failed, which means at least one condition being tested has
   failed. Ideally, it should mean a problem in the software being tested has been found.
 * ``ERROR``: An error happened during the test execution. This can happen, for example,
   if there's a bug in the test runner, in its libraries or if a resource breaks unexpectedly.
   Uncaught exceptions in the test code will also result in this status.
 * ``SKIP``: The test runner decided a requested test should not be run. This
   can happen, for example, due to missing requirements in the test environment
   or when there's a job timeout.
 * ``WARN``: The test ran and something might have gone wrong but didn't explicitly failed.
 * ``CANCEL``: The test was canceled and didn't run.
 * ``INTERRUPTED``: The test was explicitly interrupted. Usually this means that a user
   hit CTRL+C while the job was still running or did not finish before the timeout specified.

Exit codes
----------

Avocado exit code tries to represent different things that can happen during an
execution. That means exit codes can be a combination of codes that were ORed
together as a single exit code. The final exit code can be de-bundled so users
can have a good idea on what happened to the job.

The single individual exit codes are:

* :data:`AVOCADO_ALL_OK <avocado.core.exit_codes.AVOCADO_ALL_OK>`
* :data:`AVOCADO_TESTS_FAIL <avocado.core.exit_codes.AVOCADO_TEST_FAIL>`
* :data:`AVOCADO_JOB_FAIL <avocado.core.exit_codes.AVOCADO_JOB_FAIL>`
* :data:`AVOCADO_FAIL <avocado.core.exit_codes.AVOCADO_FAIL>`
* :data:`AVOCADO_JOB_INTERRUPTED <avocado.core.exit_codes.AVOCADO_JOB_INTERRUPTED>`

If a job finishes with exit code `9`, for example, it means we had at least one
test that failed and also we had at some point a job interruption, probably due
to the job timeout or a `CTRL+C`.
