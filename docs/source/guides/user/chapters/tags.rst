Filtering tests by tags
=======================

Avocado allows tests to be given tags, which can be used to create test
categories. With tags set, users can select a subset of the tests found by the
test resolver (also known as test loader).

Usually, listing and executing tests with the Avocado test runner
would reveal all three tests::

  $ avocado list perf.py
  INSTRUMENTED perf.py:Disk.test_device
  INSTRUMENTED perf.py:Network.test_latency
  INSTRUMENTED perf.py:Network.test_throughput
  INSTRUMENTED perf.py:Idle.test_idle

If you want to list or run only the network based tests, you can do so
by requesting only tests that are tagged with ``net``::

  $ avocado list perf.py --filter-by-tags=net
  INSTRUMENTED perf.py:Network.test_latency
  INSTRUMENTED perf.py:Network.test_throughput

Now, suppose you're not in an environment where you're confortable
running a test that will write to your raw disk devices (such as your
development workstation).  You know that some tests are tagged
with ``safe`` while others are tagged with ``unsafe``.  To only
select the "safe" tests you can run::

  $ avocado list perf.py --filter-by-tags=safe
  INSTRUMENTED perf.py:Network.test_latency
  INSTRUMENTED perf.py:Network.test_throughput

But you could also say that you do **not** want the "unsafe" tests
(note the *minus* sign before the tag)::

  $ avocado list perf.py --filter-by-tags=-unsafe
  INSTRUMENTED perf.py:Network.test_latency
  INSTRUMENTED perf.py:Network.test_throughput


.. tip:: The ``-`` sign may cause issues with some shells.  One know
   error condition is to use spaces between ``--filter-by-tags`` and
   the negated tag, that is, ``--filter-by-tags -unsafe`` will most
   likely not work.  To be on the safe side, use
   ``--filter-by-tags=-tag``.


If you require tests to be tagged with **multiple** tags, just add
them separate by commas.  Example::

  $ avocado list perf.py --filter-by-tags=disk,slow,superuser,unsafe
  INSTRUMENTED perf.py:Disk.test_device

If no test contains **all tags** given on a single `--filter-by-tags`
parameter, no test will be included::

  $ avocado list perf.py --filter-by-tags=disk,slow,superuser,safe | wc -l
  0

Multiple tags (AND vs OR)
-------------------------

While multiple tags in a single option will require tests with all the
given tags (effectively a logical AND operation), it's also possible
to use multiple ``--filter-by-tags`` (effectively a logical OR
operation).

For instance To include all tests that have the ``disk`` tag and all
tests that have the ``net`` tag, you can run::

  $ avocado list perf.py --filter-by-tags=disk --filter-by-tags=net
  INSTRUMENTED perf.py:Disk.test_device
  INSTRUMENTED perf.py:Network.test_latency
  INSTRUMENTED perf.py:Network.test_throughput

Including tests without tags
----------------------------

The normal behavior when using ``--filter-by-tags`` is to require the
given tags on all tests.  In some situations, though, it may be
desirable to include tests that have no tags set.

For instance, you may want to include tests of certain types that do
not have support for tags (such as SIMPLE tests) or tests that have
not (yet) received tags.  Consider this command::

  $ avocado list perf.py /bin/true --filter-by-tags=disk
  INSTRUMENTED perf.py:Disk.test_device

Since it requires the ``disk`` tag, only one test was returned.  By
using the ``--filter-by-tags-include-empty`` option, you can force the
inclusion of tests without tags::

  $ avocado list perf.py /bin/true --filter-by-tags=disk --filter-by-tags-include-empty
  SIMPLE       /bin/true
  INSTRUMENTED perf.py:Idle.test_idle
  INSTRUMENTED perf.py:Disk.test_device

Using further categorization with keys and values
-------------------------------------------------

All the examples given so far are limited to "flat" tags.  Sometimes, it's
helpful to categorize tests with extra context.  For instance, if you have
tests that are sensitive to the platform endianess, you may way to categorize
them by endianess, while at the same time, specifying the exact type of
endianess that is required.


For instance, your tags can now have a key and value pair, like:
``endianess:little`` or ``endianess:big``.

To list tests without any type of filtering would give you::

  $ avocado list byteorder.py
  INSTRUMENTED byteorder.py:ByteOrder.test_le
  INSTRUMENTED byteorder.py:ByteOrder.test_be
  INSTRUMENTED byteorder.py:Generic.test

To list tests that are somehow related to endianess, you can use::

  $ avocado list byteorder.py --filter-by-tags endianess
  INSTRUMENTED byteorder.py:ByteOrder.test_le
  INSTRUMENTED byteorder.py:ByteOrder.test_be

And to be even more specific, you can use::

  $ avocado list byteorder.py --filter-by-tags endianess:big
  INSTRUMENTED byteorder.py:ByteOrder.test_be

Now, suppose you intend to run tests on a little endian platform, but you'd
still want to include tests that are generic enough to run on either little or
big endian (but not tests that are specific to other types of endianess), you
could use::

  $ avocado list byteorder.py --filter-by-tags endianess:big --filter-by-tags-include-empty-key
  INSTRUMENTED byteorder.py:ByteOrder.test_be
  INSTRUMENTED byteorder.py:Generic.test


.. seealso:: If you would like to understand how write plugins and how describe
  tags inside a plugin, please visit the section: `Writing Tests` on Avocado Test
  Writer's Guide.
