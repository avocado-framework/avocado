================================
 New Test Types Plugin Examples
================================

Subdirectories of this folder contains "plugins" of at least two
different types:

 * resolvers: they resolve references into proper test descriptions
   that Avocado can run

 * runners: these make use of the resolutions made by resolvers and
   actually execute the tests, reporting the results back to Avocado

These are all based on the "nrunner" architecture.  To see them in
effect, after enabling them with ``python setup.py develop --user``-like
commands (see parent directory ``README.rst``), you will want to
list tests with::

  avocado list --resolver $REFERENCE

And run tests with::

  avocado run --test-runner=nrunner $REFERENCE
