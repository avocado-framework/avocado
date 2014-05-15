.. _writing-tests:

=====================
Writing Avocado Tests
=====================

Avocado tests closely resemble autotest tests: All you need to do is to create a
test module, which is a python file with a class that inherits from
:class:`avocado.test.Test`. This class only really needs to implement a method
called `action`, which represents the actual test payload.

Simple example
==============

Let's re-create an old time favorite, ``sleeptest``, which is a functional
test for avocado (old because we also use such a test for autotest). It does
nothing but ``time.sleep([number-seconds])``::

    #!/usr/bin/python

    import time

    from avocado import job
    from avocado import test


    class sleeptest(test.Test):

        """
        Example test for avocado.
        """
        default_params = {'sleep_length': 1.0}

        def action(self):
            """
            Sleep for length seconds.
            """
            self.log.debug("Sleeping for %.2f seconds", self.params.sleep_length)
            time.sleep(self.params.sleep_length)


    if __name__ == "__main__":
        job.main()

This is about the simplest test you can write for avocado (at least, one using
the avocado APIs). Note that the test object provides you with a number of
convenience attributes, such as ``self.log``, that lets you log debug, info, error
and warning messages. Also, we note the parameter passing system that avocado provides:
We frequently want to pass parameters to tests, and we can do that through what
we call a `multiplex file`, which is a configuration file that not only allows you
to provide params to your test, but also easily create a validation matrix in a
concise way. You can find more about the multiplex file format on :doc:`MultiplexConfig`.

Accessing test parameters
=========================

Each test has a set of parameters that can be accessed through ``self.params.[param-name]``.
Avocado finds and populates ``self.params`` with all parameters you define on a Multiplex
Config file (see :doc:`MultiplexConfig`), in a way that they are available as attributes,
not just dict keys. This has the advantage of reducing the boilerplate code necessary to
access those parameters. As an example, consider the following multiplex file for sleeptest::

    variants:
        - sleeptest:
            sleep_length_type = float
            variants:
                - short:
                    sleep_length = 0.5
                - medium:
                    sleep_length = 1
                - long:
                    sleep_length = 5

You may notice some things here: there is one test param to sleeptest, called ``sleep_length``. We could have named it
``length`` really, but I prefer to create a param namespace of sorts here. Then, I defined
``sleep_length_type``, that is used by the config system to convert a value (by default a
:class:`basestring`) to an appropriate value type (in this case, we need to pass a :class:`float`
to :func:`time.sleep` anyway). Note that this is an optional feature, and you can always use
:func:`float` to convert the string value coming from the configuration anyway.

Another important design detail is that sometimes we might not want to use the config system
at all (for example, when we run an avocado test as a stand alone test). To account for this
case, we have to specify a ``default_params`` dictionary that contains the default values
for when we are not providing config from a multiplex file.

Using a multiplex file
======================

You may use the avocado runner with a multiplex file to provide params and matrix
generation for sleeptest just like::

    $ avocado run sleeptest --multiplex tests/sleeptest/sleeptest.mplx
    DEBUG LOG: /home/lmr/avocado/logs/run-2014-05-13-15.44.54/debug.log
    TOTAL TESTS: 3
    (1/3) sleeptest.short:  PASS (0.64 s)
    (2/3) sleeptest.medium:  PASS (1.11 s)
    (3/3) sleeptest.long:  PASS (5.12 s)
    TOTAL PASSED: 3
    TOTAL ERROR: 0
    TOTAL FAILED: 0
    TOTAL SKIPPED: 0
    TOTAL WARNED: 0
    ELAPSED TIME: 6.87 s

Note that, as your multiplex file specifies all parameters for sleeptest, you can simply
leave the test url list empty, such as::

    $ avocado run --multiplex tests/sleeptest/sleeptest.mplx

If you want to run some tests that don't require params set by the multiplex file, you can::

    $ avocado run "sleeptest synctest" --multiplex tests/sleeptest/sleeptest.mplx
    DEBUG LOG: /home/lmr/avocado/logs/run-2014-05-13-15.47.55/debug.log
    TOTAL TESTS: 4
    (1/4) sleeptest.short:  PASS (0.61 s)
    (2/4) sleeptest.medium:  PASS (1.11 s)
    (3/4) sleeptest.long:  PASS (5.11 s)
    (4/4) synctest.1:  PASS (1.85 s)
    TOTAL PASSED: 4
    TOTAL ERROR: 0
    TOTAL FAILED: 0
    TOTAL SKIPPED: 0
    TOTAL WARNED: 0
    ELAPSED TIME: 8.69 s

Avocado tests are also unittests
================================

Since avocado tests inherit from :class:`unittest.TestCase`, you can use all
the :func:`assert` class methods on your tests. Some silly examples::

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
============================

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
=========================

If you need to perform setup actions before/after your test, you may do so
in the ``setup`` and ``cleanup`` methods, respectively. We'll give examples
in the following section.

Running third party test suites
===============================

It is very common in test automation workloads to use test suites developed
by third parties. By wrapping the execution code inside an avocado test module,
you gain access to the facilities and API provided by the framework. Let's
say you want to pick up a test suite written in C that it is in a tarball,
uncompress it, compile the suite code, and then executing the test. Here's
an example that does that::

    #!/usr/bin/python

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
        default_params = {'sync_tarball': 'synctest.tar.bz2',
                          'sync_length': 100,
                          'sync_loop': 10}

        def setup(self):
            """
            Set default params and build the synctest suite.
            """
            # Build the synctest suite
            self.cwd = os.getcwd()
            tarball_path = self.get_deps_path(self.params.sync_tarball)
            archive.extract(tarball_path, self.srcdir)
            self.srcdir = os.path.join(self.srcdir, 'synctest')
            build.make(self.srcdir)

        def action(self):
            """
            Execute synctest with the appropriate params.
            """
            os.chdir(self.srcdir)
            cmd = ('./synctest %s %s' %
                   (self.params.sync_length, self.params.sync_loop))
            process.system(cmd)
            os.chdir(self.cwd)


    if __name__ == "__main__":
        job.main()

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
=======

While there are certainly other resources that can be used to build your tests,
we recommend you take a look at the example tests present in the ``tests``
directory, that contains a few samples to take some inspiration. It is also
recommended that you take a look at the :doc:`API documentation <api/modules>`
for more possibilities.
