Writing Avocado Tests with Python
=================================

We are going to write an Avocado test in Python and we are going to inherit from
:class:`avocado.Test`. This makes this test a so-called instrumented test.

Basic example
-------------

Let's re-create an old time favorite, ``sleeptest`` [#f1]_.  It is so simple, it
does nothing besides sleeping for a while::

        import time

        from avocado import Test

        class SleepTest(Test):

            def test(self):
                sleep_length = self.params.get('sleep_length', default=1)
                self.log.debug("Sleeping for %.2f seconds", sleep_length)
                time.sleep(sleep_length)

This is about the simplest test you can write for Avocado, while still
leveraging its API power.

As can be seen in the example above, an Avocado test is a method that starts
with ``test`` in a class that inherits from :mod:`avocado.Test`.

Multiple tests and naming conventions
-------------------------------------

You can have multiple tests in a single class.

To do so, just give the methods names that start with ``test``, say
``test_foo``, ``test_bar`` and so on. We recommend you follow this naming
style, as defined in the `PEP8 Function Names`_ section.

For the class name, you can pick any name you like, but we also recommend
that it follows the CamelCase convention, also known as CapWords, defined
in the PEP 8 document under `Class Names`_.

Convenience Attributes
----------------------

Note that the test class provides you with a number of convenience attributes:

* A ready to use log mechanism for your test, that can be accessed by means
  of ``self.log``. It lets you log debug, info, error and warning messages.
* A parameter passing system (and fetching system) that can be accessed by
  means of ``self.params``. This is hooked to the Varianter, about which
  you can find that more information at :ref:`test-parameter`.
* And many more (see `avocado.core.test.Test`)

To minimize the accidental clashes we define the public ones as properties
so if you see something like ``AttributeError: can't set attribute`` double
you are not overriding these.

.. _Test statuses:

Test statuses
-------------

Avocado supports the most common exit statuses:

* ``PASS`` - test passed, there were no untreated exceptions
* ``WARN`` - a variant of ``PASS`` that keeps track of noteworthy events
  that ultimately do not affect the test outcome. An example could be
  ``soft lockup`` present in the ``dmesg`` output. It's not related to the
  test results and unless there are failures in the test it means the feature
  probably works as expected, but there were certain condition which might
  be nice to review. (some result plugins does not support this and report
  ``PASS`` instead)
* ``SKIP`` - the test's pre-requisites were not satisfied and the test's
  body was not executed (nor its ``setUp()`` and ``tearDown``).
* ``CANCEL`` - the test was canceled somewhere during the ``setUp()``, the
  test method or the ``tearDown()``. The ``setUp()`` and ``tearDown``
  methods are executed.
* ``FAIL`` - test did not result in the expected outcome. A failure points
  at a (possible) bug in the tested subject, and not in the test itself.
  When the test (and its) execution breaks, an ``ERROR`` and not a ``FAIL``
  is reported."
* ``ERROR`` - this points (probably) at a bug in the test itself, and not
  in the subject being tested.It is usually caused by uncaught exception
  and such failures needs to be thoroughly explored and should lead to
  test modification to avoid this failure or to use ``self.fail`` along
  with description how the subject under testing failed to perform it's
  task.
* ``INTERRUPTED`` - this result can't be set by the test writer, it is
  only possible when the timeout is reached or when the user hits
  ``CTRL+C`` while executing this test.
* other - there are some other internal test statuses, but you should not
  ever face them.

As you can see the ``FAIL`` is a neat status, if tests are developed
correctly. When writing tests always think about what its ``setUp``
should be, what the ``test body`` and is expected to go wrong in the
test. To support you Avocado supports several methods:

Test methods
------------

The simplest way to set the status is to use ``self.fail``,
``self.error`` or ``self.cancel`` directly from test.

To remember a warning, one simply writes to ``self.log.warning``
logger. This won't interrupt the test execution, but it will
remember the condition and, if there are no failures, will
report the test as ``WARN``.

Turning errors into failures
----------------------------

Errors on Python code are commonly signaled in the form of exceptions
being thrown.  When Avocado runs a test, any unhandled exception will
be seen as a test ``ERROR``, and not as a ``FAIL``.

Still, it's common to rely on libraries, which usually raise custom
(or builtin) exceptions. Those exceptions would normally result in
``ERROR`` but if you are certain this is an odd behavior of the
object under testing, you should catch the exception and explain
the failure in ``self.fail`` method::

    try:
        process.run("stress_my_feature")
    except process.CmdError as details:
        self.fail("The stress comamnd failed: %s" % details)

If your test compounds of many executions and you can't get this exception
in other case then expected failure, you can simplify the code by using
``fail_on`` decorator::

    @avocado.fail_on(process.CmdError)
    def test(self):
        process.run("first cmd")
        process.run("second cmd")
        process.run("third cmd")

Once again, keeping your tests up-to-date and distinguishing between
``FAIL`` and ``ERROR`` will save you a lot of time while reviewing the
test results.

.. _turning_errors_into_cancels:

Turning errors into cancels
---------------------------
It is also possible to assume unhandled exception to be as a test ``CANCEL``
instead of a test ``ERROR`` simply by using ``cancel_on`` decorator::

    def test(self):
        @avocado.cancel_on(TypeError)
        def foo():
            raise TypeError
        foo()

.. _saving-test-generated-custom-data:

Saving test generated (custom) data
-----------------------------------

Each test instance provides a so called ``whiteboard``. It can be accessed
through ``self.whiteboard``. This whiteboard is simply a string that will be
automatically saved to test results after the test finishes (it's not synced
during the execution so when the machine or Python crashes badly it might
not be present and one should use direct io to the ``outputdir`` for
critical data). If you choose to save binary data to the whiteboard,
it's your responsibility to encode it first (base64 is the obvious choice).

Building on the previously demonstrated ``sleeptest``, suppose that you want to save the
sleep length to be used by some other script or data analysis tool::

        def test(self):
            sleep_length = self.params.get('sleep_length', default=1)
            self.log.debug("Sleeping for %.2f seconds", sleep_length)
            time.sleep(sleep_length)
            self.whiteboard = "%.2f" % sleep_length

The whiteboard can and should be exposed by files generated by the available test result
plugins. The ``results.json`` file already includes the whiteboard for each test.
Additionally, we'll save a raw copy of the whiteboard contents on a file 
``$RESULTS/test-results/$TEST_ID/whiteboard``, for your convenience (maybe you want to use the 
result of a benchmark directly with your custom made scripts to analyze that
particular benchmark result).

If you need to attach several output files, you can also use
``self.outputdir``, which points to the
``$RESULTS/test-results/$TEST_ID/data`` location and is reserved for
arbitrary test result data.

.. _accessing-test-data-files:

Accessing test data files
-------------------------

Some tests can depend on data files, external to the test file itself.
Avocado provides a test API that makes it really easy to access such
files: :meth:`get_data() <avocado.core.test.TestData.get_data>`.

For Avocado tests (that is, ``INSTRUMENTED`` tests)
:meth:`get_data() <avocado.core.test.TestData.get_data>` allows test data files
to be accessed from up to three sources:

 * **file** level data directory: a directory named after the test file, but
   ending with ``.data``.  For a test file ``/home/user/test.py``, the file level
   data directory is ``/home/user/test.py.data/``.

 * **test** level data directory: a directory named after the test file and the
   specific test name.  These are useful when different tests part of the
   same file need different data files (with the same name or not).  Considering
   the previous example of ``/home/user/test.py``, and supposing it contains two
   tests, ``MyTest.test_foo`` and ``MyTest.test_bar``, the test level data
   directories will be, ``/home/user/test.py.data/MyTest.test_foo/`` and
   ``home/user/test.py.data/MyTest.test_bar/`` respectively.

 * **variant** level data directory: if variants are being used during the test
   execution, a directory named after the variant will also be considered when
   looking for test data files.  For test file ``/home/user/test.py``, and test
   ``MyTest.test_foo``, with variant ``debug-ffff``, the data directory path
   will be ``/home/user/test.py.data/MyTest.test_foo/debug-ffff/``.

.. note:: Unlike INSTRUMENTED tests, SIMPLE tests only define ``file``
          and ``variant`` data_dirs, therefore the most-specific data-dir
          might look like ``/bin/echo.data/debug-ffff/``.

Avocado looks for data files in the order defined at
:attr:`DATA_SOURCES <avocado.core.test.TestData.DATA_SOURCES>`, which are
from most specific one, to most generic one.  That means that, if a variant
is being used, the **variant** directory is used first.  Then the **test**
level directory is attempted, and finally the **file** level directory.
Additionally you can use ``get_data(filename, must_exist=False)`` to get
expected location of a possibly non-existing file, which is useful when
you intend to create it.

.. tip:: When running tests you can use the ``--log-test-data-directories``
         command line option log the test data directories that will be used
         for that specific test and execution conditions (such as with or
         without variants).  Look for "Test data directories" in the test logs.

.. note:: The previously existing API ``avocado.core.test.Test.datadir``,
          used to allow access to the data directory based on the test file
          location only.  This API has been removed.  If, for whatever reason
          you still need to access the data directory based on the test file
          location only, you can use
          ``get_data(filename='', source='file', must_exist=False)`` instead.

.. _accessing-test-parameter:

Accessing test parameters
-------------------------

Each test has a set of parameters that can be accessed through
``self.params.get($name, $path=None, $default=None)`` where:

* name - name of the parameter (key)
* path - where to look for this parameter (when not specified uses mux-path)
* default - what to return when param not found

The path is a bit tricky. Avocado uses tree to represent parameters. In simple
scenarios you don't need to worry and you'll find all your values in default
path, but eventually you might want to check-out :ref:`test-parameter` to understand
the details.

Let's say your test receives following params (you'll learn how to execute
them in the following section)::

    $ avocado variants -m examples/tests/sleeptenmin.py.data/sleeptenmin.yaml --variants 2
    ...
    Variant 1:    /run/sleeptenmin/builtin, /run/variants/one_cycle
        /run/sleeptenmin/builtin:sleep_method => builtin
        /run/variants/one_cycle:sleep_cycles  => 1
        /run/variants/one_cycle:sleep_length  => 600
    ...

In test you can access those params by:

.. code-block:: python

    self.params.get("sleep_method")    # returns "builtin"
    self.params.get("sleep_cycles", '*', 10)    # returns 1
    self.params.get("sleep_length", "/*/variants/*"  # returns 600

.. note:: The path is important in complex scenarios where clashes might
          occur, because when there are multiple values with the same
          key matching the query Avocado raises an exception. As mentioned
          you can avoid those by using specific paths or by defining
          custom mux-path which allows specifying resolving hierarchy.
          More details can be found in :ref:`test-parameter`.


Running multiple variants of tests
----------------------------------

In the previous section we described how parameters are handled.  Now,
let's have a look at how to produce them and execute your tests with
different parameters.

The variants subsystem is what allows the creation of multiple
variations of parameters, and the execution of tests with those
parameter variations.  This subsystem is pluggable, so you might use
custom plugins to produce variants.  To keep things simple, let's
use Avocado's primary implementation, called "yaml_to_mux".

The "yaml_to_mux" plugin accepts YAML files.  Those will create a
tree-like structure, store the variables as parameters and use custom
tags to mark locations as "multiplex" domains.

Let's use ``examples/tests/sleeptenmin.py.data/sleeptenmin.yaml`` file
as an example:

.. code-block:: yaml

   sleeptenmin: !mux
       builtin:
           sleep_method: builtin
       shell:
           sleep_method: shell
   variants: !mux
       one_cycle:
           sleep_cycles: 1
           sleep_length: 600
       six_cycles:
           sleep_cycles: 6
           sleep_length: 100
       one_hundred_cycles:
           sleep_cycles: 100
           sleep_length: 6
       six_hundred_cycles:
           sleep_cycles: 600
           sleep_length: 1

Which produces following structure and parameters::

  $ avocado variants -m examples/tests/sleeptenmin.py.data/sleeptenmin.yaml --summary 2 --variants 2
  Multiplex tree representation:
   ┗━━ run
        ┣━━ sleeptenmin
        ┃    ╠══ builtin
        ┃    ║     → sleep_method: builtin
        ┃    ╚══ shell
        ┃          → sleep_method: shell
        ┗━━ variants
             ╠══ one_cycle
             ║     → sleep_length: 600
             ║     → sleep_cycles: 1
             ╠══ six_cycles
             ║     → sleep_length: 100
             ║     → sleep_cycles: 6
             ╠══ one_hundred_cycles
             ║     → sleep_length: 6
             ║     → sleep_cycles: 100
             ╚══ six_hundred_cycles
                   → sleep_length: 1
                   → sleep_cycles: 600

  Multiplex variants (8):

  Variant builtin-one_cycle-f659:    /run/sleeptenmin/builtin, /run/variants/one_cycle
      /run/sleeptenmin/builtin:sleep_method => builtin
      /run/variants/one_cycle:sleep_cycles  => 1
      /run/variants/one_cycle:sleep_length  => 600

  Variant builtin-six_cycles-723b:    /run/sleeptenmin/builtin, /run/variants/six_cycles
      /run/sleeptenmin/builtin:sleep_method => builtin
      /run/variants/six_cycles:sleep_cycles => 6
      /run/variants/six_cycles:sleep_length => 100

  Variant builtin-one_hundred_cycles-633a:    /run/sleeptenmin/builtin, /run/variants/one_hundred_cycles
      /run/sleeptenmin/builtin:sleep_method         => builtin
      /run/variants/one_hundred_cycles:sleep_cycles => 100
      /run/variants/one_hundred_cycles:sleep_length => 6

  Variant builtin-six_hundred_cycles-a570:    /run/sleeptenmin/builtin, /run/variants/six_hundred_cycles
      /run/sleeptenmin/builtin:sleep_method         => builtin
      /run/variants/six_hundred_cycles:sleep_cycles => 600
      /run/variants/six_hundred_cycles:sleep_length => 1

  Variant shell-one_cycle-55f5:    /run/sleeptenmin/shell, /run/variants/one_cycle
      /run/sleeptenmin/shell:sleep_method  => shell
      /run/variants/one_cycle:sleep_cycles => 1
      /run/variants/one_cycle:sleep_length => 600

  Variant shell-six_cycles-9e23:    /run/sleeptenmin/shell, /run/variants/six_cycles
      /run/sleeptenmin/shell:sleep_method   => shell
      /run/variants/six_cycles:sleep_cycles => 6
      /run/variants/six_cycles:sleep_length => 100

  Variant shell-one_hundred_cycles-586f:    /run/sleeptenmin/shell, /run/variants/one_hundred_cycles
      /run/sleeptenmin/shell:sleep_method           => shell
      /run/variants/one_hundred_cycles:sleep_cycles => 100
      /run/variants/one_hundred_cycles:sleep_length => 6

  Variant shell-six_hundred_cycles-1e84:    /run/sleeptenmin/shell, /run/variants/six_hundred_cycles
      /run/sleeptenmin/shell:sleep_method           => shell
      /run/variants/six_hundred_cycles:sleep_cycles => 600
      /run/variants/six_hundred_cycles:sleep_length => 1

You can see that it creates all possible variants of each ``multiplex domain``,
which are defined by ``!mux`` tag in the YAML file and displayed as single
lines in tree view (compare to double lines which are individual nodes with
values). In total it'll produce 8 variants of each test::

      $ avocado run --mux-yaml examples/tests/sleeptenmin.py.data/sleeptenmin.yaml -- passtest.py
      JOB ID     : cc7ef22654c683b73174af6f97bc385da5a0f02f
      JOB LOG    : $HOME/avocado/job-results/job-2017-01-22T11.26-cc7ef22/job.log
       (1/8) passtest.py:PassTest.test;builtin-one_cycle-f659: PASS (0.01 s)
       (2/8) passtest.py:PassTest.test;builtin-six_cycles-723b: PASS (0.01 s)
       (3/8) passtest.py:PassTest.test;builtin-one_hundred_cycles-633a: PASS (0.01 s)
       (4/8) passtest.py:PassTest.test;builtin-six_hundred_cycles-a570: PASS (0.01 s)
       (5/8) passtest.py:PassTest.test;shell-one_cycle-55f5: PASS (0.01 s)
       (6/8) passtest.py:PassTest.test;shell-six_cycles-9e23: PASS (0.01 s)
       (7/8) passtest.py:PassTest.test;shell-one_hundred_cycles-586f: PASS (0.01 s)
       (8/8) passtest.py:PassTest.test;shell-six_hundred_cycles-1e84: PASS (0.01 s)
      RESULTS    : PASS 8 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
      JOB TIME   : 0.16 s

There are other options to influence the params so please check out
``avocado run -h`` and for details use :ref:`test-parameter`.


:class:`unittest.TestCase` heritage
-----------------------------------

Since an Avocado test inherits from :class:`unittest.TestCase`, you
can use all the assertion methods that its parent.

The code example bellow uses :meth:`assertEqual
<unittest.TestCase.assertEqual>`, :meth:`assertTrue
<unittest.TestCase.assertTrue>` and :meth:`assertIsInstace
<unittest.TestCase.assertIsInstance>`::

    from avocado import Test

    class RandomExamples(Test):
        def test(self):
            self.log.debug("Verifying some random math...")
            four = 2 * 2
            four_ = 2 + 2
            self.assertEqual(four, four_, "something is very wrong here!")

            self.log.debug("Verifying if a variable is set to True...")
            variable = True
            self.assertTrue(variable)

            self.log.debug("Verifying if this test is an instance of test.Test")
            self.assertIsInstance(self, test.Test)

Running tests under other :mod:`unittest` runners
-------------------------------------------------

`nose <https://nose.readthedocs.org/>`__ is another Python testing framework
that is also compatible with :mod:`unittest`.

Because of that, you can run Avocado tests with the ``nosetests`` application::

    $ nosetests examples/tests/sleeptest.py
    .
    ----------------------------------------------------------------------
    Ran 1 test in 1.004s

    OK

Conversely, you can also use the standard :func:`unittest.main` entry point to run an
Avocado test. Check out the following code, to be saved as ``dummy.py``::

   from avocado import Test
   from unittest import main

   class Dummy(Test):
       def test(self):
           self.assertTrue(True)

   if __name__ == '__main__':
       main()

It can be run by::

   $ python dummy.py
   .
   ----------------------------------------------------------------------
   Ran 1 test in 0.000s

   OK

But we'd still recommend using ``avocado.main`` instead which is our main entry point.

.. _Setup and cleanup methods:

Setup and cleanup methods
-------------------------

To perform setup actions before/after your test, you may use ``setUp``
and ``tearDown`` methods. The ``tearDown`` method is always executed
even on ``setUp`` failure so don't forget to initialize your variables
early in the ``setUp``. Example of usage is in the next section
`Running third party test suites`_.

Running third party test suites
-------------------------------

It is very common in test automation workloads to use test suites developed
by third parties. By wrapping the execution code inside an Avocado test module,
you gain access to the facilities and API provided by the framework. Let's
say you want to pick up a test suite written in C that it is in a tarball,
uncompress it, compile the suite code, and then executing the test. Here's
an example that does that::

        #!/usr/bin/env python

        import os

        from avocado import Test
        from avocado.utils import archive, build, process


        class SyncTest(Test):

            """
            Execute the synctest test suite.

            :param sync_tarball: path to the tarball relative to a data directory
            :param default_symbols: whether to build with debug symbols (bool)
            :param sync_length: how many data should by used in sync test
            :param sync_loop: how many writes should be executed in sync test
            """

            def setUp(self):
                """
                Build the synctest suite.
                """
                self.cwd = os.getcwd()
                sync_tarball = self.params.get('sync_tarball', '*', 'synctest.tar.bz2')
                tarball_path = self.get_data(sync_tarball)
                if tarball_path is None:
                    self.cancel('Test is missing data file %s' % tarball_path)
                archive.extract(tarball_path, self.workdir)
                srcdir = os.path.join(self.workdir, 'synctest')
                os.chdir(srcdir)
                if self.params.get('debug_symbols', default=True):
                    build.make(srcdir,
                               env={'CFLAGS': '-g -O0'},
                               extra_args='synctest',
                               allow_output_check='none')
                else:
                    build.make(srcdir,
                               allow_output_check='none')

            def test(self):
                """
                Execute synctest with the appropriate params.
                """
                path = os.path.join(os.getcwd(), 'synctest')
                cmd = ('%s %s %s' %
                       (path, self.params.get('sync_length', default=100),
                        self.params.get('sync_loop', default=10)))
                process.system(cmd)
                os.chdir(self.cwd)

Here we have an example of the ``setUp`` method in action: Here we get the
location of the test suite code (tarball) through
:func:`avocado.Test.get_data`, then uncompress the tarball through
:func:`avocado.utils.archive.extract`, an API that will
decompress the suite tarball, followed by :func:`avocado.utils.build.make`, that will build
the suite.

In this example, the ``test`` method just gets into the base directory of
the compiled suite  and executes the ``./synctest`` command, with appropriate
parameters, using :func:`avocado.utils.process.system`.

.. _Fetching asset files:

Fetching asset files
--------------------

To run third party test suites as mentioned above, or for any other purpose,
we offer an asset fetcher as a method of Avocado Test class.
The asset fetch method looks for a list of directories in the ``cache_dirs``
key, inside the ``[datadir.paths]`` section from the configuration files.
Read-only directories are also supported. When the asset file is not present in
any of the provided directories, Avocado will try to download the file from the
provided locations, copying it to the first writable cache directory. Example::

    cache_dirs = ['/usr/local/src/', '~/avocado/data/cache']

In the example above, ``/usr/local/src/`` is a read-only directory. In that
case, when Avocado needs to fetch the asset from the locations, the asset will
be copied to the ``~/avocado/data/cache`` directory.

If the tester does not provide a ``cache_dirs`` for the test execution, Avocado
creates a ``cache`` directory inside the Avocado ``data_dir`` location to put
the fetched files in.

* Use case 1: no ``cache_dirs`` key in config files, only the asset name
  provided in the full URL format::

    ...
        def setUp(self):
            stress = 'https://fossies.org/linux/privat/stress-1.0.4.tar.gz'
            tarball = self.fetch_asset(stress)
            archive.extract(tarball, self.workdir)
    ...

  In this case, ``fetch_asset()`` will download the file from the URL provided,
  copying it to the ``$data_dir/cache`` directory. The ``fetch_asset()`` method
  returns the target location of the fetched asset. In this example, the
  ``tarball`` variable  holds
  ``/home/user/avocado/data/cache/stress-1.0.4.tar.gz``.

* Use case 2: Read-only cache directory provided. ``cache_dirs = ['/mnt/files']``::

    ...
        def setUp(self):
            stress = 'https://fossies.org/linux/privat/stress-1.0.4.tar.gz'
            tarball = self.fetch_asset(stress)
            archive.extract(tarball, self.workdir)
    ...

  In this case, Avocado tries to find ``stress-1.0.4.tar.gz`` file in
  ``/mnt/files`` directory. If it's not found, since ``/mnt/files`` cache is
  read-only, Avocado tries to download the asset file to the ``$data_dir/cache``
  directory.

* Use case 3: Writable cache directory provided, along with a list of
  locations. Use of the default cache directory,
  ``cache_dirs = ['~/avocado/data/cache']``::

    ...
        def setUp(self):
            st_name = 'stress-1.0.4.tar.gz'
            st_hash = 'e1533bc704928ba6e26a362452e6db8fd58b1f0b'
            st_loc = ['https://fossies.org/linux/privat/stress-1.0.4.tar.gz',
                      'ftp://foo.bar/stress-1.0.4.tar.gz']
            tarball = self.fetch_asset(st_name, asset_hash=st_hash,
                                       locations=st_loc)
            archive.extract(tarball, self.workdir)
    ...

  In this case, Avocado tries to download ``stress-1.0.4.tar.gz`` from the
  provided locations list (if it's not already in the default cache,
  ``~/avocado/data/cache``). As the hash was also provided, Avocado verifies
  the hash. To do so, Avocado first looks for a hash file named
  ``stress-1.0.4.tar.gz.CHECKSUM`` in the same directory. If the hash file is
  not available, Avocado computes the hash and creates the hash file for later
  use.

  The resulting ``tarball`` variable content will be
  ``~/avocado/cache/stress-1.0.4.tar.gz``.
  An exception is raised if Avocado fails to download or to verify the file.

* Use case 4: Low bandwidth available for download of a large file which takes
  a lot of time to download and causes a CI, like Travis, for example, to
  timeout the test execution. Do not cancel the test if the file is not available::

    ...
        def setUp(self):
            st_name = 'stress-1.0.4.tar.gz'
            st_hash = 'e1533bc704928ba6e26a362452e6db8fd58b1f0b'
            st_loc = ['https://fossies.org/linux/privat/stress-1.0.4.tar.gz',
                      'ftp://foo.bar/stress-1.0.4.tar.gz']
            tarball = self.fetch_asset(st_name, asset_hash=st_hash,
                                       locations=st_loc, find_only=True)
            archive.extract(tarball, self.workdir)
    ...

  Setting the ``find_only`` parameter to ``True`` will make Avocado look for
  the asset in the cache, but will not attempt to download it if the asset
  is not available. The asset download can be done prior to the test execution
  using the command-line ``avocado assets fetch INSTRUMENTED``.

  In this example, if the asset is not available in the cache, the test will
  continue to run and when the test tries to use the asset, it will fail. A
  solution for that is presented in the next use case.

* Use case 5: Low bandwidth available for download or a large file which takes
  a lot of time to download and causes a CI, like Travis, for example, to
  timeout the test execution. Cancel the test if the file is not available::

    ...
        def setUp(self):
            st_name = 'stress-1.0.4.tar.gz'
            st_hash = 'e1533bc704928ba6e26a362452e6db8fd58b1f0b'
            st_loc = ['https://fossies.org/linux/privat/stress-1.0.4.tar.gz',
                      'ftp://foo.bar/stress-1.0.4.tar.gz']
            tarball = self.fetch_asset(st_name, asset_hash=st_hash,
                                       locations=st_loc, find_only=True,
                                       cancel_on_missing=True)
            archive.extract(tarball, self.workdir)
    ...

  With ``cancel_on_missing`` set to ``True`` and ``find_only`` set to
  ``True``, if the file is not available in the cache, the test is canceled.


Detailing the ``fetch_asset()`` parameters:

* ``name:`` The destination name used to the fetched file. It can also contains
  a full URI. The URI will be used as the location (after searching into the
  cache directories).
* ``asset_hash:`` (optional) The expected hash for the file. If missing,
  Avocado skips the hash check. If provided, before computing the hash,
  Avocado looks for a hash file to verify the asset. If the hash file is not
  available, Avocado computes the hash and creates the hash file in the same
  cache directory for later use.
* ``algorithm:`` (optional) Provided hash algorithm format. Defaults to sha1.
* ``locations:`` (optional) List of locations used to try to fetch the file.
  The supported schemes are ``http://``, ``https://``, ``ftp://`` and
  ``file://``. The tester should inform the full url to the file, including the
  file name. The first fetch success skips the next locations. Notice that for
  ``file://`` Avocado creates a symbolic link in the cache directory, pointing
  to the original location of the file.
* ``expire:`` (optional) period while a cached file is considered valid. After
  that period, the file will be downloaded again. The value can be an integer or
  a string containing the time and the unit. Example: '10d' (ten days). Valid
  units are ``s`` (second), ``m`` (minute), ``h`` (hour) and  ``d`` (day).
* ``find_only:`` (optional) tries to find the asset in the cache. If the asset
  file is not available in the cache, Avocado will not attempt to download it.
* ``cancel_on_missing`` (optional) if set to ``True``, cancel the current
  running test if there is a problem while downloading the asset or if
  ``find_only=True`` and the asset is not available in the cache.

The expected ``return`` of the method is the asset file path or an exception.

.. _output_check_record:

Test Output Check and Output Record Mode
----------------------------------------

In a lot of occasions, you want to go simpler: just check if the output of a
given test matches an expected output.  In order to help with this common
use case, Avocado provides the ``--output-check-record`` option:

.. code-block:: none

  --output-check-record {none,stdout,stderr,both,combined,all}
                        Record the output produced by each test (from stdout
                        and stderr) into both the current executing result and
                        into reference files. Reference files are used on
                        subsequent runs to determine if the test produced the
                        expected output or not, and the current executing
                        result is used to check against a previously recorded
                        reference file. Valid values: 'none' (to explicitly
                        disable all recording) 'stdout' (to record standard
                        output *only*), 'stderr' (to record standard error
                        *only*), 'both' (to record standard output and error
                        in separate files), 'combined' (for standard output
                        and error in a single file). 'all' is also a valid but
                        deprecated option that is a synonym of 'both'.

If this option is used, Avocado will store the content generated by
the test in the standard (POSIX) streams, that is, ``STDOUT`` and
``STDERR``.  Depending on the option chosen, you may end up with different
files recorded (into what we call "reference files"):

 * ``stdout`` will produce a file named ``stdout.expected`` with the
   contents from the test process standard output stream (file
   descriptor 1)
 * ``stderr`` will produce a file named ``stderr.expected`` with the
   contents from the test process standard error stream (file
   descriptor 2)
 * ``both`` will produce both a file named ``stdout.expected`` and a
   file named ``stderr.expected``
 * ``combined``: will produce a single file named ``output.expected``,
   with the content from both test process standard output and error
   streams (file descriptors 1 and 2)
 * ``none`` will explicitly disable all recording of test generated
   output and the generation reference files with that content

The reference files will be recorded in the first (most specific)
test's data dir (:ref:`accessing-test-data-files`). Let's take as an
example the test ``synctest.py``.  In a fresh checkout of the Avocado
source code you can find the following reference files::

  examples/tests/synctest.py.data/stderr.expected
  examples/tests/synctest.py.data/stdout.expected

From those 2 files, only stdout.expected has some content::

  $ cat examples/tests/synctest.py.data/stdout.expected
  PAR : waiting
  PASS : sync interrupted

This means that during a previous test execution, output was recorded
with option ``--output-check-record both`` and content was generated
on the ``STDOUT`` stream only::

  $ avocado run --output-check-record both synctest.py
  JOB ID     : b6306504351b037fa304885c0baa923710f34f4a
  JOB LOG    : $JOB_RESULTS_DIR/job-2017-11-26T16.42-b630650/job.log
   (1/1) examples/tests/synctest.py:SyncTest.test: PASS (2.03 s)
  RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
  JOB TIME   : 2.26 s

After the reference files are added, the check process is transparent,
in the sense that you do not need to provide special flags to the test
runner.  From this point on, after such as test (one with a reference
file recorded) has finished running, Avocado will check if the output
generated match the reference(s) file(s) content.  If they don't
match, the test will finish with a ``FAIL`` status.

You can disable this automatic check when a reference file exists by
passing ``--disable-output-check`` to the test runner.

.. tip:: The :mod:`avocado.utils.process` APIs have a parameter called
         ``allow_output_check`` that let you individually select the
         output that will be part of the test output and recorded
         reference files.  Some other APIs built on top of
         :mod:`avocado.utils.process`, such as the ones in
         :mod:`avocado.utils.build` also provide the same parameter.

This process works fine also with simple tests, which are programs or shell scripts
that returns 0 (PASSed) or != 0 (FAILed). Let's consider our bogus example::

    $ cat output_check.sh
    #!/bin/bash
    echo "Hello, world!"

Let's record the output for this one::

    $ avocado run output_check.sh --output-check-record all
    JOB ID    : 25c4244dda71d0570b7f849319cd71fe1722be8b
    JOB LOG   : $HOME/avocado/job-results/job-2014-09-25T20.49-25c4244/job.log
     (1/1) output_check.sh: PASS (0.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB TIME   : 0.11 s

After this is done, you'll notice that the test data directory
appeared in the same level of our shell script, containing 2 files::

    $ ls output_check.sh.data/
    stderr.expected  stdout.expected

Let's look what's in each of them::

    $ cat output_check.sh.data/stdout.expected
    Hello, world!
    $ cat output_check.sh.data/stderr.expected
    $

Now, every time this test runs, it'll take into account the expected files that
were recorded, no need to do anything else but run the test. Let's see what
happens if we change the ``stdout.expected`` file contents to ``Hello, Avocado!``::

    $ avocado run output_check.sh
    JOB ID    : f0521e524face93019d7cb99c5765aedd933cb2e
    JOB LOG   : $HOME/avocado/job-results/job-2014-09-25T20.52-f0521e5/job.log
     (1/1) output_check.sh: FAIL (0.02 s)
    RESULTS    : PASS 0 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
    JOB TIME   : 0.12 s

Verifying the failure reason::

    $ cat $HOME/avocado/job-results/latest/job.log
	2017-10-16 14:23:02,567 test             L0381 INFO | START 1-output_check.sh
	2017-10-16 14:23:02,568 test             L0402 DEBUG| Test metadata:
	2017-10-16 14:23:02,568 test             L0403 DEBUG|   filename: $HOME/output_check.sh
	2017-10-16 14:23:02,596 process          L0389 INFO | Running '$HOME/output_check.sh'
	2017-10-16 14:23:02,603 process          L0499 INFO | Command '$HOME/output_check.sh' finished with 0 after 0.00131011009216s
	2017-10-16 14:23:02,602 process          L0479 DEBUG| [stdout] Hello, world!
	2017-10-16 14:23:02,603 test             L1084 INFO | Exit status: 0
	2017-10-16 14:23:02,604 test             L1085 INFO | Duration: 0.00131011009216
	2017-10-16 14:23:02,604 test             L0274 DEBUG| DATA (filename=stdout.expected) => $HOME/output_check.sh.data/stdout.expected (found at file source dir)
	2017-10-16 14:23:02,605 test             L0740 DEBUG| Stdout Diff:
	2017-10-16 14:23:02,605 test             L0742 DEBUG| --- $HOME/output_check.sh.data/stdout.expected
	2017-10-16 14:23:02,605 test             L0742 DEBUG| +++ $HOME/avocado/job-results/job-2017-10-16T14.23-8cba866/test-results/1-output_check.sh/stdout
	2017-10-16 14:23:02,605 test             L0742 DEBUG| @@ -1 +1 @@
	2017-10-16 14:23:02,605 test             L0742 DEBUG| -Hello, Avocado!
	2017-10-16 14:23:02,605 test             L0742 DEBUG| +Hello, world!
	2017-10-16 14:23:02,606 stacktrace       L0041 ERROR|
	2017-10-16 14:23:02,606 stacktrace       L0044 ERROR| Reproduced traceback from: $HOME/git/avocado/avocado/core/test.py:872
	2017-10-16 14:23:02,606 stacktrace       L0047 ERROR| Traceback (most recent call last):
	2017-10-16 14:23:02,606 stacktrace       L0047 ERROR|   File "$HOME/git/avocado/avocado/core/test.py", line 743, in _check_reference_stdout
	2017-10-16 14:23:02,606 stacktrace       L0047 ERROR|     self.fail('Actual test sdtout differs from expected one')
	2017-10-16 14:23:02,606 stacktrace       L0047 ERROR|   File "$HOME//git/avocado/avocado/core/test.py", line 983, in fail
	2017-10-16 14:23:02,607 stacktrace       L0047 ERROR|     raise exceptions.TestFail(message)
	2017-10-16 14:23:02,607 stacktrace       L0047 ERROR| TestFail: Actual test sdtout differs from expected one
	2017-10-16 14:23:02,607 stacktrace       L0048 ERROR|
	2017-10-16 14:23:02,607 test             L0274 DEBUG| DATA (filename=stderr.expected) => $HOME//output_check.sh.data/stderr.expected (found at file source dir)
	2017-10-16 14:23:02,608 test             L0965 ERROR| FAIL 1-output_check.sh -> TestFail: Actual test sdtout differs from expected one


As expected, the test failed because we changed its expectations, so an
unified diff was logged. The unified diffs are also present in the files
`stdout.diff` and `stderr.diff`, present in the test results directory::

	$ cat $HOME/avocado/job-results/latest/test-results/1-output_check.sh/stdout.diff
	--- $HOME/output_check.sh.data/stdout.expected
	+++ $HOME/avocado/job-results/job-2017-10-16T14.23-8cba866/test-results/1-output_check.sh/stdout
	@@ -1 +1 @@
	-Hello, Avocado!
	+Hello, world!


.. note:: Currently the `stdout`, `stderr` and `output` files are
          stored in text mode.  Data that can not be decoded according
          to current locale settings, will be replaced according to
          https://docs.python.org/3/library/codecs.html#codecs.replace_errors.


Test log, stdout and stderr in native Avocado modules
-----------------------------------------------------

If needed, you can write directly to the expected stdout and stderr files
from the native test scope. It is important to make the distinction between
the following entities:

* The test logs
* The test expected stdout
* The test expected stderr

The first one is used for debugging and informational purposes. Additionally
writing to `self.log.warning` causes test to be marked as dirty and when
everything else goes well the test ends with WARN. This means that the test
passed but there were non-related unexpected situations described in warning
log.

You may log something into the test logs using the methods in
:mod:`avocado.Test.log` class attributes. Consider the example::

    class output_test(Test):

        def test(self):
            self.log.info('This goes to the log and it is only informational')
            self.log.warn('Oh, something unexpected, non-critical happened, '
                          'but we can continue.')
            self.log.error('Describe the error here and don't forget to raise '
                           'an exception yourself. Writing to self.log.error '
                           'won't do that for you.')
            self.log.debug('Everybody look, I had a good lunch today...')

If you need to write directly to the test stdout and stderr streams,
Avocado makes two preconfigured loggers available for that purpose,
named ``avocado.test.stdout`` and ``avocado.test.stderr``. You can use
Python's standard logging API to write to them. Example::

    import logging

    class output_test(Test):

        def test(self):
            stdout = logging.getLogger('avocado.test.stdout')
            stdout.info('Informational line that will go to stdout')
            ...
            stderr = logging.getLogger('avocado.test.stderr')
            stderr.info('Informational line that will go to stderr')

Avocado will automatically save anything a test generates on STDOUT
into a ``stdout`` file, to be found at the test results directory. The same
applies to anything a test generates on STDERR, that is, it will be saved
into a ``stderr`` file at the same location.

Additionally, when using the runner's output recording features,
namely the ``--output-check-record`` argument with values ``stdout``,
``stderr`` or ``all``, everything given to those loggers will be saved
to the files ``stdout.expected`` and ``stderr.expected`` at the test's
data directory (which is different from the job/test results directory).

Setting a Test Timeout
----------------------

Sometimes your test suite/test might get stuck forever, and this might
impact your test grid. You can account for that possibility and set up a
``timeout`` parameter for your test. The test timeout can be set through
the test parameters, as shown below.

::

    sleep_length: 5
    timeout: 3


::

    $ avocado run sleeptest.py --mux-yaml /tmp/sleeptest-example.yaml
    JOB ID     : c78464bde9072a0b5601157989a99f0ba32a288e
    JOB LOG    : $HOME/avocado/job-results/job-2016-11-02T11.13-c78464b/job.log
     (1/1) sleeptest.py:SleepTest.test: INTERRUPTED (3.04 s)
    RESULTS    : PASS 0 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 1
    JOB TIME   : 3.14 s
    JOB HTML   : $HOME/avocado/job-results/job-2016-11-02T11.13-c78464b/html/results.html


::

	$ cat $HOME/avocado/job-results/job-2016-11-02T11.13-c78464b/job.log
	2016-11-02 11:13:01,133 job              L0384 INFO | Multiplex tree representation:
	2016-11-02 11:13:01,133 job              L0386 INFO |  \-- run
	2016-11-02 11:13:01,133 job              L0386 INFO |         -> sleep_length: 5
	2016-11-02 11:13:01,133 job              L0386 INFO |         -> timeout: 3
	2016-11-02 11:13:01,133 job              L0387 INFO | 
	2016-11-02 11:13:01,134 job              L0391 INFO | Temporary dir: /var/tmp/avocado_PqDEyC
	2016-11-02 11:13:01,134 job              L0392 INFO | 
	2016-11-02 11:13:01,134 job              L0399 INFO | Variant 1:    /run
	2016-11-02 11:13:01,134 job              L0402 INFO | 
	2016-11-02 11:13:01,134 job              L0311 INFO | Job ID: c78464bde9072a0b5601157989a99f0ba32a288e
	2016-11-02 11:13:01,134 job              L0314 INFO | 
	2016-11-02 11:13:01,345 sysinfo          L0107 DEBUG| Not logging /proc/pci (file does not exist)
	2016-11-02 11:13:01,351 sysinfo          L0105 DEBUG| Not logging /proc/slabinfo (lack of permissions)
	2016-11-02 11:13:01,355 sysinfo          L0107 DEBUG| Not logging /sys/kernel/debug/sched_features (file does not exist)
	2016-11-02 11:13:01,388 sysinfo          L0388 INFO | Commands configured by file: /etc/avocado/sysinfo/commands
	2016-11-02 11:13:01,388 sysinfo          L0399 INFO | Files configured by file: /etc/avocado/sysinfo/files
	2016-11-02 11:13:01,388 sysinfo          L0419 INFO | Profilers configured by file: /etc/avocado/sysinfo/profilers
	2016-11-02 11:13:01,388 sysinfo          L0427 INFO | Profiler disabled
	2016-11-02 11:13:01,394 multiplexer      L0166 DEBUG| PARAMS (key=timeout, path=*, default=None) => 3
	2016-11-02 11:13:01,395 test             L0216 INFO | START 1-sleeptest.py:SleepTest.test
	2016-11-02 11:13:01,396 multiplexer      L0166 DEBUG| PARAMS (key=sleep_length, path=*, default=1) => 5
	2016-11-02 11:13:01,396 sleeptest        L0022 DEBUG| Sleeping for 5.00 seconds
	2016-11-02 11:13:04,411 stacktrace       L0038 ERROR| 
	2016-11-02 11:13:04,412 stacktrace       L0041 ERROR| Reproduced traceback from: $HOME/src/avocado/avocado/core/test.py:454
	2016-11-02 11:13:04,412 stacktrace       L0044 ERROR| Traceback (most recent call last):
	2016-11-02 11:13:04,413 stacktrace       L0044 ERROR|   File "/usr/share/doc/avocado/tests/sleeptest.py", line 23, in test
	2016-11-02 11:13:04,413 stacktrace       L0044 ERROR|     time.sleep(sleep_length)
	2016-11-02 11:13:04,413 stacktrace       L0044 ERROR|   File "$HOME/src/avocado/avocado/core/runner.py", line 293, in sigterm_handler
	2016-11-02 11:13:04,413 stacktrace       L0044 ERROR|     raise SystemExit("Test interrupted by SIGTERM")
	2016-11-02 11:13:04,414 stacktrace       L0044 ERROR| SystemExit: Test interrupted by SIGTERM
	2016-11-02 11:13:04,414 stacktrace       L0045 ERROR| 
	2016-11-02 11:13:04,414 test             L0459 DEBUG| Local variables:
	2016-11-02 11:13:04,440 test             L0462 DEBUG|  -> self <class 'sleeptest.SleepTest'>: 1-sleeptest.py:SleepTest.test
	2016-11-02 11:13:04,440 test             L0462 DEBUG|  -> sleep_length <type 'int'>: 5
	2016-11-02 11:13:04,440 test             L0592 ERROR| ERROR 1-sleeptest.py:SleepTest.test -> TestError: SystemExit('Test interrupted by SIGTERM',): Test interrupted by SIGTERM


The YAML file defines a test parameter ``timeout`` which overrides
the default test timeout before the runner ends the test forcefully by
sending a class:`signal.SIGTERM` to the test, making it raise a
:class:`avocado.core.exceptions.TestTimeoutError`.


Skipping Tests
--------------

To skip tests is in Avocado, you must use one of the Avocado skip
decorators:

- :func:`avocado.skip`: Skips a test.
- :func:`avocado.skipIf`: Skips a test if the condition is ``True``.
- :func:`avocado.skipUnless`: Skips a test if the condition is ``False``

Those decorators can be used with classes and both ``setUp()`` method and/or and in the
``test*()`` methods. The test below::

    import avocado

    class MyTest(avocado.Test):

        @avocado.skipIf(1 == 1, 'Skipping on True condition.')
        def test1(self):
            pass

        @avocado.skip("Don't want this test now.")
        def test2(self):
            pass

        @avocado.skipUnless(1 == 1, 'Skipping on False condition.')
        def test3(self):
            pass

Will produce the following result::

    $ avocado run  test_skip_decorators.py
    JOB ID     : 59c815f6a42269daeaf1e5b93e52269fb8a78119
    JOB LOG    : $HOME/avocado/job-results/job-2017-02-03T17.41-59c815f/job.log
     (1/3) test_skip_decorators.py:MyTest.test1: SKIP
     (2/3) test_skip_decorators.py:MyTest.test2: SKIP
     (3/3) test_skip_decorators.py:MyTest.test3: PASS (0.02 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 2 | WARN 0 | INTERRUPT 0
    JOB TIME   : 0.13 s
    JOB HTML   : $HOME/avocado/job-results/job-2017-02-03T17.41-59c815f/html/results.html

Notice the ``test3`` was not skipped because the provided condition was
not ``False``.

Using the skip decorators, nothing is actually executed. We will skip
the  ``setUp()`` method, the test method and the ``tearDown()`` method.

.. note:: It's an erroneous condition, reported with test status
          ``ERROR``, to use any of the skip decorators on the
          ``tearDown()`` method.

.. _skip-advanced-conditionals:

Advanced Conditionals
~~~~~~~~~~~~~~~~~~~~~

More advanced use cases may require to evaluate the condition for
skipping tests later, and may also need to introspect into the
class that contains the test method in question.

It's possible to achieve both by supplying a callable to the condition
parameters instead.  The following example does just that:

.. literalinclude:: ../../../../../examples/tests/skip_conditional.py

Even though the conditions for skipping tests are defined in the
``BaseTest`` class, the conditions will be evaluated when the tests
are actually checked for execution, in the ``BareMetal`` and
``NonBareMetal`` classes.  The result of running that test is::

    JOB ID     : 77d636c93ed3b5e6fef9c7b6c8d9fe0c84af1518
    JOB LOG    : $HOME/avocado/job-results/job-2021-03-17T20.10-77d636c/job.log
     (01/10) skip_conditional.py:BareMetal.test_specific: PASS (0.00 s)
     (02/10) skip_conditional.py:BareMetal.test_bare_metal: PASS (0.00 s)
     (03/10) skip_conditional.py:BareMetal.test_large_memory: SKIP: Not enough memory for test
     (04/10) skip_conditional.py:BareMetal.test_nested_virtualization: SKIP: Virtual Machine environment is required
     (05/10) skip_conditional.py:BareMetal.test_container: SKIP: Container environment is required
     (06/10) skip_conditional.py:NonBareMetal.test_specific: PASS (0.00 s)
     (07/10) skip_conditional.py:NonBareMetal.test_bare_metal: SKIP: Bare metal environment is required
     (08/10) skip_conditional.py:NonBareMetal.test_large_memory: SKIP: Not enough memory for test
     (09/10) skip_conditional.py:NonBareMetal.test_nested_virtualization: PASS (0.00 s)
     (10/10) skip_conditional.py:NonBareMetal.test_container: PASS (0.00 s)
    RESULTS    : PASS 5 | ERROR 0 | FAIL 0 | SKIP 5 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB HTML   : $HOME/avocado/job-results/job-2021-03-17T20.10-77d636c/results.html
    JOB TIME   : 0.82 s

Canceling Tests
----------------

You can cancel a test calling `self.cancel()` at any phase of the test
(`setUp()`, test method or `tearDown()`). Test will finish with `CANCEL`
status and will not make the Job to exit with a non-0 status. Example::


    from avocado import Test

    from avocado.utils.process import run
    from avocado.utils.software_manager import SoftwareManager


    class CancelTest(Test):

        """
        Example tests that cancel the current test from inside the test.
        """

        def setUp(self):
            sm = SoftwareManager()
            self.pkgs = sm.list_all(software_components=False)

        def test_iperf(self):
            if 'iperf-2.0.8-6.fc25.x86_64' not in self.pkgs:
                self.cancel('iperf is not installed or wrong version')
            self.assertIn('pthreads',
                          run('iperf -v', ignore_status=True).stderr)

        def test_gcc(self):
            if 'gcc-6.3.1-1.fc25.x86_64' not in self.pkgs:
                self.cancel('gcc is not installed or wrong version')
            self.assertIn('enable-gnu-indirect-function',
                          run('gcc -v', ignore_status=True).stderr)

In a system missing the `iperf` package but with `gcc` installed in
the correct version, the result will be::

    $ avocado run cancel_test.py
    JOB ID     : 39c1f120830b9769b42f5f70b6b7bad0b1b1f09f
    JOB LOG    : $HOME/avocado/job-results/job-2017-03-10T16.22-39c1f12/job.log
     (1/2) /home/apahim/avocado/tests/test_cancel.py:CancelTest.test_iperf: CANCEL (1.15 s)
     (2/2) /home/apahim/avocado/tests/test_cancel.py:CancelTest.test_gcc: PASS (1.13 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 1
    JOB TIME   : 2.38 s
    JOB HTML   : $HOME/avocado/job-results/job-2017-03-10T16.22-39c1f12/html/results.html

Notice that using the ``self.cancel()`` will cancel the rest of the test
from that point on, but the ``tearDown()`` will still be executed.

Depending on the result format you're referring to, the ``CANCEL`` status
is mapped to a corresponding valid status in that format. See the table
below:

+--------+----------------------+
| Format | Corresponding Status |
+========+======================+
| json   | cancel               |
+--------+----------------------+
| xunit  | skipped              |
+--------+----------------------+
| tap    | ok                   |
+--------+----------------------+
| html   | CANCEL (warning)     |
+--------+----------------------+

Docstring Directives
--------------------

Some Avocado features, usually only available to instrumented tests,
depend on setting directives on the test's class docstring.  A
docstring directive is composed of a marker (a literal ``:avocado:`` string),
followed by the custom content itself, such as ``:avocado: directive``.

This is similar to docstring directives such as ``:param my_param:
description`` and shouldn't be a surprise to most Python developers.

The reason Avocado uses those docstring directives (instead of real
Python code) is that the inspection done while looking for tests does
not involve any execution of code.

For a detailed explanation about what makes a docstring format valid
or not, please refer to our section on :ref:`docstring-directive-rules`.

Now let's follow with some docstring directives examples.

.. _docstring-directive-enable-disable:

Declaring test as NOT-INSTRUMENTED
----------------------------------

In order to say `this class is not an Avocado instrumented` test, one
can use ``:avocado: disable`` directive. The result is that this
class itself is not discovered as an instrumented test, but children
classes might inherit it's ``test*`` methods (useful for base-classes)::

   from avocado import Test

   class BaseClass(Test):
       """
       :avocado: disable
       """
       def test_shared(self):
           pass

   class SpecificTests(BaseClass):
       def test_specific(self):
           pass

Results in::

   $ avocado list test.py
   INSTRUMENTED test.py:SpecificTests.test_specific
   INSTRUMENTED test.py:SpecificTests.test_shared

The ``test.py:BaseBase.test`` is not discovered due the tag while
the ``test.py:SpecificTests.test_shared`` is inherited from the
base-class.


Declaring test as INSTRUMENTED
------------------------------

The ``:avocado: enable`` tag might be useful when you want to
override that this is an `INSTRUMENTED` test, even though it is
not inherited from ``avocado.Test`` class and/or when you want
to only limit the ``test*`` methods discovery to the current
class::

   from avocado import Test

   class NotInheritedFromTest:
       """
       :avocado: enable
       """
       def test(self):
           pass

   class BaseClass(Test):
       """
       :avocado: disable
       """
       def test_shared(self):
           pass

   class SpecificTests(BaseClass):
       """
       :avocado: enable
       """
       def test_specific(self):
           pass

Results in::

   $ avocado list test.py
   INSTRUMENTED test.py:NotInheritedFromTest.test
   INSTRUMENTED test.py:SpecificTests.test_specific

The ``test.py:NotInheritedFromTest.test`` will not really work
as it lacks several required methods, but still is discovered
as an `INSTRUMENTED` test due to ``enable`` tag and the
``SpecificTests`` only looks at it's ``test*`` methods,
ignoring the inheritance, therefor the
``test.py:SpecificTests.test_shared`` will not be discovered.


(Deprecated) enabling recursive discovery
-----------------------------------------

The ``:avocado: recursive`` tag was used to enable recursive
discovery, but nowadays this is the default. By using this
tag one explicitly sets the class as `INSTRUMENTED`, therefor
inheritance from `avocado.Test` is not required.


.. _categorizing-tests:

Categorizing tests
------------------

Avocado allows tests to be given tags, which can be used to create
test categories.  With tags set, users can select a subset of the
tests found by the test resolver (also known as test loader).

To make this feature easier to grasp, let's work with an example: a
single Python source code file, named ``perf.py``, that contains both
disk and network performance tests::

  from avocado import Test

  class Disk(Test):

      """
      Disk performance tests

      :avocado: tags=disk,slow,superuser,unsafe
      """

      def test_device(self):
          device = self.params.get('device', default='/dev/vdb')
          self.whiteboard = measure_write_to_disk(device)


  class Network(Test):

      """
      Network performance tests

      :avocado: tags=net,fast,safe
      """

      def test_latency(self):
          self.whiteboard = measure_latency()

      def test_throughput(self):
          self.whiteboard = measure_throughput()


  class Idle(Test):

      """
      Idle tests
      """

      def test_idle(self):
          self.whiteboard = "test achieved nothing"


.. warning:: All docstring directives in Avocado require a strict
             format, that is, ``:avocado:`` followed by one or
             more spaces, and then followed by a single value **with no
             white spaces in between**.  This means that an attempt to
             write a docstring directive like ``:avocado: tags=foo,
             bar`` will be interpreted as ``:avocado: tags=foo,``.


.. _categorizing-tests-tags-on-methods:

Test tags can be applied to test classes and to test methods. Tags are
evaluated per method, meaning that the class tags will be inherited by
all methods, being merged with method local tags. Example::

    from avocado import Test

    class MyClass(Test):
        """
        :avocado: tags=furious
        """

        def test1(self):
            """
            :avocado: tags=fast
            """
            pass

        def test2(self):
            """
            :avocado: tags=slow
            """
            pass

If you use the tag ``furious``, all tests will be included::

    $ avocado list furious_tests.py --filter-by-tags=furious
    INSTRUMENTED test_tags.py:MyClass.test1
    INSTRUMENTED test_tags.py:MyClass.test2

But using ``fast`` and ``furious`` will include only ``test1``::

    $ avocado list furious_tests.py --filter-by-tags=fast,furious
    INSTRUMENTED test_tags.py:MyClass.test1


.. _tags_keyval:

Python :mod:`unittest` Compatibility Limitations And Caveats
------------------------------------------------------------

When executing tests, Avocado uses different techniques than most
other Python unittest runners.  This brings some compatibility
limitations that Avocado users should be aware.

Execution Model
~~~~~~~~~~~~~~~

One of the main differences is a consequence of the Avocado design
decision that tests should be self contained and isolated from other
tests.  Additionally, the Avocado test runner runs each test in a
separate process.

If you have a unittest class with many test methods and run them
using most test runners, you'll find that all test methods run under
the same process.  To check that behavior you could add to your
:meth:`setUp <unittest.TestCase.setUp>` method::

   def setUp(self):
       print("PID: %s", os.getpid())

If you run the same test under Avocado, you'll find that each test
is run on a separate process.

Class Level :meth:`setUp <unittest.TestCase.setUpClass>` and :meth:`tearDown <unittest.TestCase.tearDownClass>`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Because of Avocado's test execution model (each test is run on a
separate process), it doesn't make sense to support unittest's
:meth:`unittest.TestCase.setUpClass` and
:meth:`unittest.TestCase.tearDownClass`.  Test classes are freshly
instantiated for each test, so it's pointless to run code in those
methods, since they're supposed to keep class state between tests.

The ``setUp`` method is the only place in Avocado where you are allowed to
call the ``skip`` method, given that, if a test started to be executed, by
definition it can't be skipped anymore. Avocado will do its best to enforce
this boundary, so that if you use ``skip`` outside ``setUp``, the test upon
execution will be marked with the ``ERROR`` status, and the error message
will instruct you to fix your test's code.

If you require a common setup to a number of tests, the current
recommended approach is to to write regular :meth:`setUp
<unittest.TestCase.setUp>` and :meth:`tearDown
<unittest.TestCase.tearDown>` code that checks if a given state was
already set.  One example for such a test that requires a binary
installed by a package::

  from avocado import Test

  from avocado.utils import software_manager
  from avocado.utils import path as utils_path
  from avocado.utils import process


  class BinSleep(Test):

      """
      Sleeps using the /bin/sleep binary
      """
      def setUp(self):
          self.sleep = None
          try:
              self.sleep = utils_path.find_command('sleep')
          except utils_path.CmdNotFoundError:
              software_manager.install_distro_packages({'fedora': ['coreutils']})
              self.sleep = utils_path.find_command('sleep')

      def test(self):
          process.run("%s 1" % self.sleep)

If your test setup is some kind of action that will last across
processes, like the installation of a software package given in the
previous example, you're pretty much covered here.

If you need to keep other type of data a class across test
executions, you'll have to resort to saving and restoring the data
from an outside source (say a "pickle" file).  Finding and using a
reliable and safe location for saving such data is currently not in
the Avocado supported use cases.

.. _environment-variables-for-tests:

Environment Variables for Tests
-------------------------------

Avocado exports some information, including test parameters, as environment
variables to the running test.

While these variables are available to all tests, they are usually
more interesting to SIMPLE tests.  The reason is that SIMPLE tests can
not make direct use of Avocado API.  INSTRUMENTED tests will usually
have more powerful ways, to access the same information.

Here is a list of the variables that Avocado currently exports to
tests:

+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| Environment Variable        | Meaning                               | Example                                                                                             |
+=============================+=======================================+=====================================================================================================+
| AVOCADO_VERSION             | Version of Avocado test runner        | 0.12.0                                                                                              |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| AVOCADO_TEST_BASEDIR        | Base directory of Avocado tests       | $HOME/Downloads/avocado-source/avocado                                                              |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| AVOCADO_TEST_WORKDIR        | Work directory for the test           | /var/tmp/avocado_Bjr_rd/my_test.sh                                                                  |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| AVOCADO_TESTS_COMMON_TMPDIR | Temporary directory created by the    | /var/tmp/avocado_XhEdo/                                                                             |
|                             | `teststmpdir` plugin. The directory   |                                                                                                     |
|                             | is persistent throughout the tests    |                                                                                                     |
|                             | in the same Job                       |                                                                                                     |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| AVOCADO_TEST_LOGDIR         | Log directory for the test            | $HOME/logs/job-results/job-2014-09-16T14.38-ac332e6/test-results/$HOME/my_test.sh.1                 |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| AVOCADO_TEST_LOGFILE        | Log file for the test                 | $HOME/logs/job-results/job-2014-09-16T14.38-ac332e6/test-results/$HOME/my_test.sh.1/debug.log       |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| AVOCADO_TEST_OUTPUTDIR      | Output directory for the test         | $HOME/logs/job-results/job-2014-09-16T14.38-ac332e6/test-results/$HOME/my_test.sh.1/data            |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| AVOCADO_TEST_SYSINFODIR     | The system information directory      | $HOME/logs/job-results/job-2014-09-16T14.38-ac332e6/test-results/$HOME/my_test.sh.1/sysinfo         |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| `***`                       | All variables from --mux-yaml         | TIMEOUT=60; IO_WORKERS=10; VM_BYTES=512M; ...                                                       |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+

.. warning:: ``AVOCADO_TEST_SRCDIR`` was present in earlier versions,
             but has been deprecated on version 60.0, and removed on
             version 62.0.  Please use ``AVOCADO_TEST_WORKDIR``
             instead.

.. warning:: ``AVOCADO_TEST_DATADIR`` was present in earlier versions,
             but has been deprecated on version 60.0, and removed on
             version 62.0.  The test data files (and directories) are
             now dynamically evaluated and are not available as
             environment variables

SIMPLE Tests BASH extensions
----------------------------

SIMPLE tests written in shell can use a few Avocado utilities.  In your
shell code, check if the libraries are available with something like::

  AVOCADO_SHELL_EXTENSIONS_DIR=$(avocado exec-path 2>/dev/null)

And if available, injects that directory containing those utilities
into the PATH used by the shell, making those utilities readily
accessible::

  if [ $? == 0 ]; then
    PATH=$AVOCADO_SHELL_EXTENSIONS_DIR:$PATH
  fi

For a full list of utilities, take a look into at the directory return
by ``avocado exec-path`` (if any).  Also, the example test
``examples/tests/simplewarning.sh`` can serve as further inspiration.

.. tip:: These extensions may be available as a separate package.  For
         RPM packages, look for the ``bash`` sub-package.

.. _test_type_simple_status:

SIMPLE Tests Status
-------------------

With SIMPLE tests, Avocado checks the exit code of the test to determine
whether the test PASSed or FAILed.

If your test exits with exit code 0 but you still want to set a different test
status in some conditions, Avocado can search a given regular expression in
the test outputs and, based on that, set the status to WARN or SKIP.

To use that feature, you have to set the proper keys in the configuration
file. For instance, to set the test status to SKIP when the test outputs
a line like this: '11:08:24 Test Skipped'::

    [simpletests.output]
    skip_regex = ^\d\d:\d\d:\d\d Test Skipped$

That configuration will make Avocado to search the
`Python Regular Expression <http://docs.python.org/2.7/howto/regex.html>`__
on  both stdout and stderr. If you want to limit the search for only one of
them, there's another key for that configuration, resulting in::

    [simpletests.output]
    skip_regex = ^\d\d:\d\d:\d\d Test Skipped$
    skip_location = stderr

The equivalent settings can be present for the WARN status. For instance,
if you want to set the test status to WARN when the test outputs a line
starting with string ``WARNING:``, the configuration file will look like this::

    [simpletests.output]
    skip_regex = ^\d\d:\d\d:\d\d Test Skipped$
    skip_location = stderr
    warn_regex = ^WARNING:
    warn_location = all

Job Cleanup
-----------

It's possible to register a callback function that will be called when
all the tests have finished running. This effectively allows for a
test job to clean some state it may have left behind.

At the moment, this feature is not intended to be used by test writers,
but it's seen as a feature for Avocado extensions to make use.

To register a callback function, your code should put a message in a
very specific format in the "runner queue". The Avocado test runner
code will understand that this message contains a (serialized) function
that will be called once all tests finish running.

Example::

  from avocado import Test

  def my_cleanup(path_to_file):
     if os.path.exists(path_to_file):
        os.unlink(path_to_file)

  class MyCustomTest(Test):
  ...
     cleanup_file = '/tmp/my-custom-state'
     self.runner_queue.put({"func_at_exit": self.my_cleanup,
                            "args": (cleanup_file),
                            "once": True})
  ...

This results in the ``my_cleanup`` function being called with
positional argument ``cleanup_file``.

Because ``once`` was set to ``True``, only one unique combination of
function, positional arguments and keyword arguments will be
registered, not matter how many times they're attempted to be
registered. For more information check
:meth:`avocado.utils.data_structures.CallbackRegister.register`.

.. _docstring-directive-rules:

Docstring Directives Rules
--------------------------

Avocado INSTRUMENTED tests, those written in Python and using the
:class:`avocado.Test` API, can make use of special directives
specified as docstrings.

To be considered valid, the docstring must match this pattern:
:data:`avocado.core.safeloader.DOCSTRING_DIRECTIVE_RE_RAW`.

An Avocado docstring directive has two parts:

 1) The marker, which is the literal string ``:avocado:``.

 2) The content, a string that follows the marker, separated by at
    least one white space or tab.

The following is a list of rules that makes a docstring directive
be a valid one:

 * It should start with ``:avocado:``, which is the docstring
   directive "marker"

 * At least one whitespace or tab must follow the marker and precede
   the docstring directive "content"

 * The "content", which follows the marker and the space, must begin
   with an alphanumeric character, that is, characters within "a-z",
   "A-Z" or "0-9".

 * After at least one alphanumeric character, the content may contain
   the following special symbols too: ``_``, ``,``, ``=`` and ``:``.

 * An end of string (or end of line) must immediately follow the
   content.

Signal Handlers
---------------

Avocado normal operation is related to run code written by
users/test-writers. It means the test code can carry its own handlers
for different signals or even ignore then. Still, as the code is being
executed by Avocado, we have to make sure we will finish all the
subprocesses we create before ending our execution.

Signals sent to the Avocado main process will be handled as follows:

- SIGSTP/Ctrl+Z: On SIGSTP, Avocado will pause the execution of the
  subprocesses, while the main process will still be running,
  respecting the timeout timer and waiting for the subprocesses to
  finish. A new SIGSTP will make the subprocesses to resume the
  execution.

- SIGINT/Ctrl+C: This signal will be forwarded to the test process and
  Avocado will wait until it's finished. If the test process does not
  finish after receiving a SIGINT, user can send a second SIGINT (after
  the 2 seconds ignore period). The second SIGINT will make Avocado
  to send a SIGKILL to the whole subprocess tree and then complete the
  main process execution.

- SIGTERM: This signal will make Avocado to terminate immediately. A
  SIGKILL will be sent to the whole subprocess tree and the main process
  will exit without completing the execution. Notice that it's a
  best-effort attempt, meaning that in case of fork-bomb, newly created
  processes might still be left behind.

Wrap Up
-------

We recommend you take a look at the example tests present in the
``examples/tests`` directory, that contains a few samples to take some
inspiration from. That directory, besides containing examples, is also used by
the Avocado self test suite to do functional testing of Avocado itself.
Although one can inspire in `<https://github.com/avocado-framework-tests>`__
where people are allowed to share their basic system tests.

It is also recommended that you take a look at the :ref:`tests-api-reference`.
for more possibilities.

.. [#f1] sleeptest is a functional test for Avocado. It's "old" because we
	 also have had such a test for `Autotest`_ for a long time.

.. _Autotest: http://autotest.github.io
.. _Class Names: https://www.python.org/dev/peps/pep-0008/
.. _PEP8 Function Names: https://www.python.org/dev/peps/pep-0008/#function-names


