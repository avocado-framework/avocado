.. _nrunner:

N(ext)Runner
============

This section details the :mod:`avocado.core.nrunner` module, which
contains a proposal for the next Avocado test runner implementation.

Motivation
----------

There are a number of reasons for introducing a different runner
architecture and implementation.  Some of them are related to
limitations found in the current implementation, that were found
to be too hard to remove without major breakage.  Other reasons
are closely related to missing features that are deemed important.

For instance, these are the current limitations of the Avocado test
runner:

* Test execution limited to the same machine, given that the
  communication between runner and test is a Python queue (the remote
  runner plugins actually execute an Avocado Job remotely, with all
  the overhead and complications that it brings)
* Test execution is limited to a single test at a time (non-parallel)
* Test processes are not properly isolated and can affect the test
  runner (including the "UI")

And these are some features which it's believed to be more easily
implemented under a different architecture and implementation:

* Remote execution
* Different test execution isolation models provided by the test runner
  (process, container, virtual machine)
* Distributed execution of tests across a pool of any combination of
  processes, containers, virtual machines, etc.
* Parallel execution of tests
* Optimized runners for a given environment and or test type (for
  instance, a runner written in RUST to run tests written in RUST
  in an environment that already has RUST installed but not much
  else)
* Notification of execution results to many simultaneous "status
  servers"
* Disconnected test execution, so that results can be saved to a
  device and collected by the runner
* Simplified and automated deployment of the runner component into
  execution environments such as containers and virtual machines

Concepts
--------

Runnable
~~~~~~~~

A runnable is a description of an entity that can be executed and
produce some kind of result.  The description is abstract on purpose.
A simple and obvious candidate for filling the description is a
standalone executable, such as the ones available on your ``/bin``
directory.

A runnable must declare its kind.  Using the previous example of
standalone executables, those may be given the unique kind identifier
such as ``exec``.

Each runnable kind may require a different amount of information to be
provided so that it can be instantiated.  Using standalone executables
as an example, the information required should be limtied to the
location of the the standalone executable file.  The following
pseudo-code may help to put these ideas together::

  runnable_instance = create_runnable('exec', uri='/bin/true')

Runner
~~~~~~

A runner is an active entity that acts on the information of a
runnable.  A runner will usually be tied to an specific kind of
runnable, and will to able to act upon the specific information that
runnable kind provides.

The following pseudo-code may help to illustrate that::

  runnable_instance = create_runnable('exec', uri='/bin/sleep')
  if runnable_instance.kind == 'exec':
     runner = create_runner_exec(runnable_instance)

A runner should produce status information on the progress of the
execution of a runnable.  If the runnable produces interesting
information, it should forward that along.  For instance, using the
``exec`` runner example, it's helpful to start producing status
that the process has been created and it's running as soon as
possible.  These can be as simple as a sequence of::

  {"status": "running"}
  {"status": "running"}

When the process is finished, it can return::

  {"status": "finished", "returncode": 0, 'stdout': b'', 'stderr': b''}

Note that, besides the status of ``finished``, and a return code which
can be used to determine a success or failure status, it's not the
runner's responsibility to determine test results.

Task
~~~~

A task is one specific instance/occurrence of the execution of a
runnable with its respective runner.  They should have a unique
identifier, although a task by itself wont't enforce its uniqueness in
a process or any other type of collection.

A task is responsible for producing and reporting status updates.
This status updates are in a format similar to those received from a
runner, but will add more information to them, such as its unique
identifier.

A different agreggate structure should be used to keep track of the
execution of tasks.

Recipe
~~~~~~

A recipe is the serialization of the runnable information in a
file.  The format chosen is JSON, and that should allow both
quick and easy machine handling and also manual creation of
recipes when necessary.

Runners
-------

A runner can be capable of running one or many different kinds of
runnables.  A runner should implement a ``capabilities`` command
that returns, among other info, a list of runnable kinds that it
can (to the best of its knowledge) run.  Example::

  python3 -m avocado.core.nrunner capabilities
  {'runnables': ['noop', 'exec', 'exec-test', 'python-unittest'],
   'commands': ['capabilities', 'runnable-run', 'runnable-run-recipe',
   'task-run', 'task-run-recipe', 'status-server']}

Runner scripts
--------------

The primary runner implementation is a Python module that can be run,
as shown before, with the ``avocado.core.nrunner`` module name.
Additionally it's also available as the ``avocado-runner`` script.

Runner Execution
----------------

While the ``exec`` runner given as example before will need to create
an extra process to actually run the standalone executable given, that
is an implementation detail of that specific runner.  Other types of
runners may be able to run the code the users expects it to run, while
still providing feedback about it in the same process.

The runner's main method (``run()``) operates like a generator, and
yields results which are dictionaries with relevant information about
it.

Trying it out - standalone
--------------------------

It's possible to interact with the runner features by using the
command line.  This interface is not stable at all, and may be changed
or removed in the future.

You can run a "noop" runner with::

  python3 -m avocado.core.nrunner runnable-run -k noop

You can run an "exec" runner with::

  python3 -m avocado.core.nrunner runnable-run -k exec -u /bin/uname --args='-a'

You can run an "exec-test" runner with::

  python3 -m avocado.core.nrunner runnable-run -k exec-test -u /bin/true

You can run a "python-unittest" runner with::

  python3 -m avocado.core.nrunner runnable-run -k python-unittest -u unittest.TestCase

Trying it out - Avocado Plugins
-------------------------------

Simple Avocado plugins for the runner features are also available.

Runnables from parameters
~~~~~~~~~~~~~~~~~~~~~~~~~

You can run a "noop" runner with::

  avocado runnable-run -k noop

You can run an "exec" runner with::

  avocado runnable-run -k exec -u /bin/sleep -a 3

You can run an "exec-test" runner with::

  avocado runnable-run -k exec-test -u /bin/true

You can run a "python-unittest" runner with::

  avocado runnable-run python-unittest unittest.TestCase

Runnables from recipes
~~~~~~~~~~~~~~~~~~~~~~

You can run a "noop" recipe with::

  avocado runnable-run-recipe examples/recipes/runnables/noop.json

You can run an "exec" runner with::

  avocado runnable-run-recipe examples/recipes/runnables/exec_sleep_3.json

You can run a "python-unittest" runner with::

  avocado runnable-run-recipe examples/recipes/runnables/python_unittest.json
