.. _plugin_teststmpdir:

teststmpdir
===========

This plugin will create a temporary directory **on the system where
the Avocado job is running**.  This directory will be available
throughout the execution of the job.

The indented use case is for legacy test suites that have dependencies
between tests.  An early test may benefit from doing some sort of
setup, such as downloading a file or compiling some code.  The
location of this directory will be made available:

* At the environment variable ``AVOCADO_TESTS_COMMON_TMPDIR``
* At the :data:`avocado.Test.teststmpdir` property for
  ``avocado-instrumented`` tests.

By making use of the temporary directory that will precede and outlive
the test itself, the setup performed by one test may be reused by a
later test.

This is opposed to a test's own and private work directory
(environment variable ``AVOCADO_TEST_WORKDIR``, property
:data:`avocado.Test.workdir`) which will only be available during each
individual test execution.

.. warning:: if an Avocado job spawns tests with a spawner other than
             ``process`` (say ``podman``, ``lxc`` or another custom
             spawner), those tests won't have access to the common
             temporary directory created by this plugin.
