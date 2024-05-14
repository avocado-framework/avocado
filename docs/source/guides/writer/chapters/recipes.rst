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
