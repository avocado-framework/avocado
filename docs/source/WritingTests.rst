.. _writing-tests:

Writing Avocado Tests
=====================

Avocado tests closely resemble autotest tests: All you need to do is to create a
test module, which is a python file with a class that inherits from
:class:`avocado.test.Test`. This class only really needs to implement a method
called `action`, which represents the actual test payload.

Super simple example - sleeptest
--------------------------------

Let's re-create an old time favorite, sleeptest, which is a functional
test for autotest. It does nothing but `time.sleep([number-seconds])`:

::

    #!/usr/bin/python

    import time

    from avocado import job
    from avocado import test


    class sleeptest(test.Test):

        """
        Example test for avocado.
        """

        def action(self, length=1):
            """
            Sleep for length seconds.
            """
            self.log.debug("Sleeping for %d seconds", length)
            time.sleep(length)


    if __name__ == "__main__":
        job.main()


This is about the simplest test you can write for avocado (at least, one using
the avocado APIs). Note that the test object provides you with a number of
convenience attributes, such as `self.log`, that lets you log debug, info, error
and warning messages.

Avocado tests are also unittests
--------------------------------

Since avocado tests inherit from :class:`unittest.TestCase`, you can use all
the ``assert`` class methods on your tests. Some silly examples::

    class random_examples(test.Test):
        def action(self):
            self.log.debug("Verifying some random math...")
            four = 2 * 2
            four_ = 2 + 2
            self.assertEqual(four, four_, "something is very wrong here!")

            self.log.debug("Verifying if a variable is set to True...")
            variable = True
            self.assertTrue(variable)

            self.log.debug("Verifying if this test is an instance of test.Test")
            self.assertIsInstance(self, test.Test)

The reason why we have a shebang in the beginning of the test is because
avocado tests, similarly to unittests, can use an entry point, called
:func:`avocado.job.main`, that calls avocado libs to look for test classes and execute
its main entry point. This is an optional, but fairly handy feature. In case
you want to use it, don't forget to ``chmod +x`` your test.

Executing an avocado test gives::

    $ tests/sleeptest/sleeptest.py
    DEBUG LOG: /home/lmr/avocado/logs/run-2014-04-23-21.11.37/debug.log
    TOTAL TESTS: 1
    (1/1) sleeptest.1:  PASS (1.11 s)
    TOTAL PASSED: 1
    TOTAL FAILED: 0
    TOTAL SKIPPED: 0
    TOTAL WARNED: 0
    ELAPSED TIME: 1.11 s

Running tests with nosetests
----------------------------

`nose <https://nose.readthedocs.org/>`__ is a python testing framework with
similar goals as avocado, except that avocado also intends to provide tools to
assemble a fully automated test grid, plus richer test API for tests on the
Linux platform. Regardless, the fact that an avocado class is also an unittest
cass, you can run them with the ``nosetests`` application::

    $ nosetests tests/sleeptest/sleeptest.py
    .
    ----------------------------------------------------------------------
    Ran 1 test in 1.092s

    OK

Setup and cleanup methods
-------------------------

If you need to perform setup actions before/after your test, you may do so
in the ``setup`` and ``cleanup`` methods, respectively. We'll give examples
in the following section.

Building and executing 3rd party test suites
--------------------------------------------

It is very common in test automation workloads to use test suites developed
by 3rd parties. By wrapping the execution code inside an avocado test module,
you gain access to the facilities and API provided by the framework. Let's
say you want to pick up a test suite written in C that it is in a tarball,
uncompress it, compile the suite code, and then executing the test. Here's
an example that does that::

    import os

    from avocado import test
    from avocado import job
    from avocado.utils import archive
    from avocado.utils import build
    from avocado.utils import process


    class synctest(test.Test):

        """
        Execute the synctest test suite.
        """

        def setup(self, tarball='synctest.tar.bz2'):
            tarball_path = self.get_deps_path(tarball)
            archive.extract(tarball_path, self.srcdir)
            self.srcdir = os.path.join(self.srcdir, 'synctest')
            build.make(self.srcdir)

        def action(self, length=100, loop=10):
            os.chdir(self.srcdir)
            cmd = './synctest %s %s' % (length, loop)
            process.system(cmd)

Here we have an example of the ``setup`` method in action: Here we get the
location of the test suite code (tarball) through
:func:`avocado.test.Test.get_deps_path`, then uncompress the tarball through
:func:`avocado.utils.archive.extract`, an API that will
decompress the suite tarball, followed by ``build.make``, that will build the
suite.

The ``action`` method just gets into the base directory of the compiled suite
and executes the ``./synctest`` command, with appropriate parameters, using
:func:`avocado.utils.process.system`.

Wrap Up
-------

While there are certainly other resources that can be used to build your tests,
we recommend you take a look at the example tests present in the ``tests``
directory to take some inspiration. It is also recommended that you take a
look at the :doc:`API documentation <api/modules>` for more possibilities.
