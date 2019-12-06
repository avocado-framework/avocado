.. _tap-plugin:

===========
TAP Plugin
===========

This optional plugin enables Avocado to parse the output of tests that produce
the `Test Anything Protocol <https://testanything.org>`_.

The tests can be run as usual::

    $ avocado run --loaders tap -- ./mytaptest

Notice that you have to be explicit about the test loader you're using,
otherwise, since the test files are executable binaries, the FileLoader will
detect the file as a SIMPLE test, making the whole test suite to be executed
as one test only from the Avocado perspective.  Because TAP test programs
should exit with a zero exit status, this will cause the test to pass even
if there are failures.
