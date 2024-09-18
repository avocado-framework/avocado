Defining what to run using recipe files
---------------------------------------

If you've followed the previous documentation sections, you should now
be able to write ``exec-test`` tests and also ``avocado-instrumented``
tests.  These tests should be found when you run
``avocado run /reference/to/a/test``.  Internally, though, these will
be defined as a :class:`avocado.core.nrunner.runnable.Runnable`.

This is interesting because you are able to have a shortcut into what
Avocado runs by defining a ``Runnable``. Runnables can be defined using
pure Python code, such as in the following Job example:

.. literalinclude:: ../../../../../examples/jobs/custom_exec_test.py

But, they can also be defined in JSON files, which we call "runnable
recipes", such as:

.. literalinclude:: ../../../../../examples/nrunner/recipes/runnable/exec_test_sleep_3.json


Runnable recipe format
~~~~~~~~~~~~~~~~~~~~~~

While it should be somewhat easy to see the similarities between
between the fields in the
:class:`avocado.core.nrunner.runnable.Runnable` structure and a
runnable recipe JSON data, Avocado actually ships with a schema that
defines the exact format of the runnable recipe:

.. literalinclude:: ../../../../../avocado/schemas/runnable-recipe.schema.json

Avocado will attempt to enforce the JSON schema any time a
``Runnable`` is loaded from such recipe files.

Using runnable recipes as references
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Avocado ships with a ``runnable-recipe`` resolver plugin, which means
that you can use runnable recipe file as a reference, and get
something that Avocado can run (that is, a ``Runnable``).  Example::

   avocado list examples/nrunner/recipes/runnable/python_unittest.json
   python-unittest selftests/unit/test.py:TestClassTestUnit.test_long_name

And just as runnable recipe's resolution can be listed, they can also
be executed::

  avocado run examples/nrunner/recipes/runnable/python_unittest.json
  JOB ID     : bca087e0e5f16e62f24430602f87df67ecf093f7
  JOB LOG    : ~/avocado/job-results/job-2024-04-17T11.53-bca087e/job.log
   (1/1) selftests/unit/test.py:TestClassTestUnit.test_long_name: STARTED
   (1/1) selftests/unit/test.py:TestClassTestUnit.test_long_name: PASS (0.02 s)
  RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
  JOB TIME   : 2.72 s

.. tip:: As a possible integration strategy with existing tests, you
         can have one or more runnable recipe files that are passed
         to Avocado to be executed.

Combining multiple recipes in a single file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Avocado also ships with a slightly difference resolver, called
``runnables-recipe``.  It reads a recipe file that, instead of
containing one single runnable, contains (potentially) many.
It should contain nothing more than an a list of runnables.

For instance, to run both ``/bin/true`` and ``/bin/false``, you can
define a file like:

.. literalinclude:: ../../../../../examples/nrunner/recipes/runnables/true_false.json

That will be parsed by the ``runnables-recipe`` resolver, like in
``avocado list examples/nrunner/recipes/runnables/true_false.json``::

  exec-test /bin/true
  exec-test /bin/false

Using dynamically generated recipes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``exec-runnables-recipe`` resolver allows a user to point to a
file that will be executed, and that is expected to generate (on its
``STDOUT``) content compatible with the Runnable recipe format
mentioned previously.

For security reasons, Avocado won't execute files indiscriminately
when looking for tests (at the resolution phase). One must set the
``--resolver-run-executables`` command line option (or the underlying
``resolver.run_executables`` configuration option) to allow running
executables at the resolver stage.

.. warning:: It's the user's responsibility to give test references
             (to be resolved and thus executed) that are well behaved
             in the sense that they will finish executing quickly,
             won't execute unintended code (such as running tests),
             won't destroy data, etc.

A script such as:

.. literalinclude:: ../../../../../examples/nrunner/resolvers/exec_runnables_recipe.sh

Will output JSON that is compatible with the runnable recipe format.
That can be used directly via either ``avocado list`` or ``avocado
run``.  Example::

  $ avocado list --resolver-run-executables examples/nrunner/resolvers/exec_runnables_recipe.sh

  exec-test true-test
  exec-test false-test

If the executable to be run needs arguments, you can pass it via the
``--resolver-exec-arguments`` or the underlying
``resolver.exec_runnable_recipe.arguments`` option.  The following
script receives an optional parameter that can change the type of the
tests it generates:

.. literalinclude:: ../../../../../examples/nrunner/resolvers/exec_runnables_recipe_kind.sh

In order to have those tests resolved as ``tap`` tests, one can run::

  $ avocado list --resolver-run-executables --resolver-exec-arguments tap examples/nrunner/resolvers/exec_runnables_recipe_kind.sh

  tap true-test
  tap false-test

Behavior of ``exec-runnables-recipe`` and ``exec-test`` resolvers
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The ``exec-runnables-recipe`` resolver has a higher priority than
(that is, it runs before) the ``exec-test`` resolver.  That means that
if, and only if, a user enables the feature itself (by means of the
``--resolver-run-executables`` command line option or the underlying
``resolver.run_executables`` configuration option), it
``exec-runnables-recipe`` will perform any meaningful action.

Even if the ``exec-runnables-recipe`` is activated (through the
command line or configuration option mentioned before), it may still
coexist with ``exec-test`` resolver, example::

  $ avocado list --resolver-run-executables examples/nrunner/resolvers/exec_runnables_recipe.sh /bin/uname

  exec-test true-test
  exec-test false-test
  exec-test /bin/uname

The reason (that can be seen with ``avocado -V list ...``) for that is
the ``exec-runnables-recipe`` returns a "not found" resolution with
the message::

  Resolver              Reference  Info
  ...
  exec-runnables-recipe /bin/uname Content generated by running executable "/bin/uname" is not JSON

.. warning:: Even though it's possible to have ``exec-test`` and
             ``exec-runnable-recipes`` in the same Avocado test suite
             (for instance in an ``avocado run`` command execution)
             it's not recommended on most cases because ``exec-tests``
             will end up being run at the test resolution phase
             in addition to the test execution phase.  It's
             recommended to use multiple ``avocado run``
             commands or use the Job API and multiple
             :class:`avocado.core.suite.TestSuite`, one for
             ``exec-runnable-recipes`` with the
             ``resolver.run_executables`` options enabled, and
             another for ``exec-tests`` with that option in its
             default state (disabled).
