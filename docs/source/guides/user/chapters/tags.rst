Filtering tests by tags
=======================

Avocado allows tests to be given tags, which can be used to create test
categories. With tags set, users can select a subset of the tests found by the
test resolver.

Usually, listing and executing tests with the Avocado test runner
would reveal all three tests::

  $ avocado list examples/tests/tags.py
  avocado-instrumented examples/tests/tags.py:FastTest.test_fast
  avocado-instrumented examples/tests/tags.py:FastTest.test_fast_other
  avocado-instrumented examples/tests/tags.py:SlowTest.test_slow
  avocado-instrumented examples/tests/tags.py:SlowUnsafeTest.test_slow_unsafe
  avocado-instrumented examples/tests/tags.py:SafeTest.test_safe
  avocado-instrumented examples/tests/tags.py:SafeX86Test.test_safe_x86
  avocado-instrumented examples/tests/tags.py:NoTagsTest.test_no_tags
  avocado-instrumented examples/tests/tags.py:SafeAarch64Test.test_safe_aarch64

If you want to list or run only the network based tests, you can do so
by requesting only tests that are tagged with ``net``::

  $ avocado list examples/tests/tags.py --filter-by-tags=net
  avocado-instrumented examples/tests/tags.py:FastTest.test_fast
  avocado-instrumented examples/tests/tags.py:FastTest.test_fast_other

Now, suppose you're not in an environment where you're comfortable
running a test that will write to your raw disk devices (such as your
development workstation).  You know that some tests are tagged
with ``safe`` while others are tagged with ``unsafe``.  To only
select the "safe" tests you can run::

  $ avocado list examples/tests/tags.py --filter-by-tags=safe
  avocado-instrumented examples/tests/tags.py:SafeTest.test_safe
  avocado-instrumented examples/tests/tags.py:SafeX86Test.test_safe_x86
  avocado-instrumented examples/tests/tags.py:SafeAarch64Test.test_safe_aarch64

But you could also say that you do **not** want the "unsafe" tests
(note the *minus* sign before the tag)::

  $ avocado list examples/tests/tags.py --filter-by-tags=-unsafe
  avocado-instrumented examples/tests/tags.py:FastTest.test_fast
  avocado-instrumented examples/tests/tags.py:FastTest.test_fast_other
  avocado-instrumented examples/tests/tags.py:SlowTest.test_slow
  avocado-instrumented examples/tests/tags.py:SafeTest.test_safe
  avocado-instrumented examples/tests/tags.py:SafeX86Test.test_safe_x86
  avocado-instrumented examples/tests/tags.py:SafeAarch64Test.test_safe_aarch64


.. tip:: The ``-`` sign may cause issues with some shells.  One know
   error condition is to use spaces between ``--filter-by-tags`` and
   the negated tag, that is, ``--filter-by-tags -unsafe`` will most
   likely not work.  To be on the safe side, use
   ``--filter-by-tags=-tag``.


If you require tests to be tagged with **multiple** tags, just add
them separate by commas.  Example::

  $ avocado list examples/tests/tags.py --filter-by-tags=disk,slow,unsafe
  avocado-instrumented examples/tests/tags.py:SlowUnsafeTest.test_slow_unsafe

If no test contains **all tags** given on a single ``--filter-by-tags``
parameter, no test will be included::

  $ avocado list examples/tests/tags.py --filter-by-tags=disk,slow,safe | wc -l
  0

Multiple tags (AND vs OR)
-------------------------

While multiple tags in a single option will require tests with all the
given tags (effectively a logical AND operation), it's also possible
to use multiple ``--filter-by-tags`` (effectively a logical OR
operation).

For instance To include all tests that have the ``disk`` tag and all
tests that have the ``net`` tag, you can run::

  $ avocado list examples/tests/tags.py --filter-by-tags=disk --filter-by-tags=net
  avocado-instrumented examples/tests/tags.py:FastTest.test_fast
  avocado-instrumented examples/tests/tags.py:FastTest.test_fast_other
  avocado-instrumented examples/tests/tags.py:SlowTest.test_slow
  avocado-instrumented examples/tests/tags.py:SlowUnsafeTest.test_slow_unsafe

Including tests without tags
----------------------------

The normal behavior when using ``--filter-by-tags`` is to require the
given tags on all tests.  In some situations, though, it may be
desirable to include tests that have no tags set.

For instance, you may want to include tests of certain types that do
not have support for tags (such as executable tests) or tests that have
not (yet) received tags.  Consider this command::

  $ avocado list examples/tests/tags.py /bin/true --filter-by-tags=disk
  avocado-instrumented examples/tests/tags.py:SlowTest.test_slow
  avocado-instrumented examples/tests/tags.py:SlowUnsafeTest.test_slow_unsafe

Since it requires the ``disk`` tag, only one test was returned.  By
using the ``--filter-by-tags-include-empty`` option, you can force the
inclusion of tests without tags::

  $ avocado list examples/tests/tags.py /bin/true --filter-by-tags=disk --filter-by-tags-include-empty
  avocado-instrumented examples/tests/tags.py:SlowTest.test_slow
  avocado-instrumented examples/tests/tags.py:SlowUnsafeTest.test_slow_unsafe
  avocado-instrumented examples/tests/tags.py:NoTagsTest.test_no_tags
  exec-test            /bin/true

Using further categorization with keys and values
-------------------------------------------------

All the examples given so far are limited to "flat" tags.  Sometimes, it's
helpful to categorize tests with extra context.  For instance, if you have
tests that are sensitive to the platform endianness, you may way to categorize
them by endianness, while at the same time, specifying the exact type of
endianness that is required.


For instance, your tags can now have a key and value pair, like:
``endianness:little`` or ``endianness:big``.

To list tests without any type of filtering would give you::

  $ avocado list byteorder.py
  avocado-instrumented byteorder.py:ByteOrder.test_le
  avocado-instrumented byteorder.py:ByteOrder.test_be
  avocado-instrumented byteorder.py:Generic.test

To list tests that are somehow related to endianness, you can use::

  $ avocado list byteorder.py --filter-by-tags endianness
  avocado-instrumented byteorder.py:ByteOrder.test_le
  avocado-instrumented byteorder.py:ByteOrder.test_be

And to be even more specific, you can use::

  $ avocado list byteorder.py --filter-by-tags endianness:big
  avocado-instrumented byteorder.py:ByteOrder.test_be

A "negated" form is also available to filter out tests that do *not*
have a given value.  To filter out tests that have an endianness set,
but are *not* big endian you can use::

  $ avocado list byteorder.py --filter-by-tags endianness:-big
  avocado-instrumented byteorder.py:ByteOrder.test_le

Now, suppose you intend to run tests on a little endian platform, but you'd
still want to include tests that are generic enough to run on either little or
big endian (but not tests that are specific to other types of endianness), you
could use::

  $ avocado list byteorder.py --filter-by-tags endianness:big --filter-by-tags-include-empty-key
  avocado-instrumented byteorder.py:ByteOrder.test_be
  avocado-instrumented byteorder.py:Generic.test


.. seealso:: If you would like to understand how write plugins and how describe
  tags inside a plugin, please visit the :ref:`writing_tests` on Avocado Test
  Writer's Guide.
