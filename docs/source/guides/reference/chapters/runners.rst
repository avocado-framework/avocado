.. _nrunner:

The Avocado default runner (nrunner)
====================================

This section details the default Avocado suite runner called
"nrunner", also previously known as N(ext) Runner, and the
architecture around it.

.. tip:: a suite runner is an implementation of the
         :class:`avocado.core.plugin_interfaces.SuiteRunner`
         interface.  It's the component that runs one or more tests
         that are contained in a
         :class:`avocado.core.suite.TestSuite`.

At its essence, the nrunner architecture, when compared to the
previous runner architecture (now referred to as the "legacy runner")
is about making Avocado more capable and flexible.  Even though it
started with a major internal paradigm change within the test runner,
it also affects users and test writers used to the legacy runner.

The :mod:`avocado.core.nrunner` module was initially responsible for
most of the nrunner code.  As development continued, it spread around
to other places in the Avocado source tree.  Other components with
different and seemingly unrelated names, say the "resolvers" or the
"spawners", are also pretty much about the nrunner architecture.

Motivation
----------

There are a number of reasons for introducing a different architecture
and implementation.  Some of them are related to limitations found in
the legacy implementation, that were found to be too hard to remove
without major breakage.  Also, missing features that are deemed
important would be a better fit within a different architecture.

For instance, these are the limitations of the Avocado legacy test
runner:

* Test execution limited to the same machine, given that the
  communication between runner and test is a Python queue
* Test execution is limited to a single test at a time (serial
  execution)
* Test processes are not properly isolated and can affect the test
  runner (including the "UI")

And these are some features which it's believed to be more easily
implemented under a different architecture and implementation:

* Remote test execution
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

nrunner components of Avocado
-----------------------------

Whenever we mention the **current** architecture or implementation,
we are talking about the nrunner.  It includes:

* ``avocado list`` command
* ``avocado run`` command
* :mod:`avocado.core.resolver` module to resolve tests
* :mod:`avocado.core.spawners` modules to spawn tasks

Basic Avocado usage and workflow
--------------------------------

Avocado is described as "a set of tools and libraries to help with
automated testing".  The most visible aspect of Avocado is its ability
to run tests, and display the results.  We're talking about someone
doing::

  $ avocado run mytests.py othertests.sh

To be able to complete such a command, Avocado needs to find the tests, and
then to execute them.  Those two major steps are described next.

.. _finding_tests:

Finding tests
~~~~~~~~~~~~~

The first thing Avocado needs to do, before actually running any
tests, is translating the "names" given as arguments to ``avocado run``
into actual tests.  Even though those names will usually be file names,
this is not a requirement.  Avocado calls those "names" given as arguments
to ``avocado run`` "test references", because they are references that
hopefully "point to" tests.

On the nrunner architecture, each one of the test references given to
``list`` or ``run`` will be "resolved" into zero or more tests.  Being
more precise and verbose, resolver plugins will produce
:class:`avocado.core.resolver.ReferenceResolution`, which contain zero
or more :class:`avocado.core.nrunner.runnable.Runnable`, which are
described in the following section.  Overall, the process looks like::

  +--------------------+    +-----------------------+
  | avocado list | run | -> | avocado.core.resolver | ---+
  +--------------------+    +-----------------------+    |
                                                         |
    +----------------------------------------------------+
    |
    v
  +--------------------------------------+
  | ReferenceResolution #1               |
  +--------------------------------------+
  | Reference: /bin/true                 |
  | Result: SUCCESS                      |
  | +----------------------------------+ |
  | | Resolution #1 (Runnable):        | |
  | |  - kind: exec-test               | |
  | |  - uri: /bin/true                | |
  | +----------------------------------+ |
  +--------------------------------------+

  +--------------------------------------+
  | ReferenceResolution #2               |
  +--------------------------------------+
  | Reference: test.py                   |
  | Result: SUCCESS                      |
  | +----------------------------------+ |
  | | Resolution #1 (Runnable):        | |
  | |  - kind: python-unittest         | |
  | |  - uri: test.py:Test.test_1      | |
  | +----------------------------------+ |
  | +----------------------------------+ |
  | | Resolution #2 (Runnable):        | |
  | |  - kind: python-unittest         | |
  | |  - uri: test.py:Test.test_2      | |
  | +----------------------------------+ |
  +--------------------------------------+

  ...

Running Tests
~~~~~~~~~~~~~

The idea of **testing** has to do with checking the expected output of
a given action.  This action, within the realm of software development
with automated testing, has to do with the output or outcome of a
"code payload" when executed under a given controlled environment.

In the nrunner architecture, a
:class:`avocado.core.nrunner.runnable.Runnable` describe a "code
payload" that will be executed, but they are not executable code
themselves.  Because they are **data** and not **code**, they are
easily serialized and transported to different environments.  Running
the payload described by a ``Runnable`` is delegated to another
component.

Most often, this component is a standalone executable (see
:data:`avocado.core.spawners.common.SpawnMethod.STANDALONE_EXECUTABLE`)
compatible with a specific command line interface.  The most important
interfaces such scripts must implement are the ``runnable-run`` and
``task-run`` interfaces.

Once all the ``Runnable(s)`` (within the ``ReferenceResolution(s)``)
are created by :mod:`avocado.core.resolver`, the ``avocado
run --suite-runner=nrunner`` implementation follows roughly the
following steps:

1. Creates a status server that binds to a TCP port and waits for
   status messages from any number of clients
2. Creates the chosen :class:`Spawner
   <avocado.core.spawners.common.BaseSpawner>`, with
   :class:`ProcessSpawner
   <avocado.core.spawners.process.ProcessSpawner>` being the default
3. For each :class:`avocado.core.nrunner.runnable.Runnable` found by
   the resolver, turns it into a :class:`avocado.core.nrunner.Task`,
   which means giving it the following extra information:

  a. The status server(s) that it should report to
  b. An unique identification, so that its messages to the status
     server can be uniquely identified

4. For each resulting :class:`avocado.core.nrunner.Task` in the previous
   step:

  a. Asks the spawner to spawn it
  b. Asks the spawner to check if the task seems to be alive right
     after spawning it, to give the user early indication of possible
     crashes

5. Waits until all tasks have provided a ``result`` to the status
   server

If any of the concepts mentioned here were not clear, please check
their full descriptions in the next section.

Concepts
--------

Runnable
~~~~~~~~

A runnable is a description of an entity that can be executed and
produce some kind of result.  It's a passive entity that can not
execute itself and can not produce results itself.

This description of a runnable is abstract on purpose.  While the most
common use case for a Runnable is to describe how to execute a
test, there seems to be no reason to bind that concept to a
test. Other Avocado subsystems, leverage the same concept. One example is
the :ref:`sysinfo-collection` which describes what kind of system
information collection is to be performed in a ``Runnable``.

A Runnable's ``kind``
+++++++++++++++++++++

The most important information about a runnable is the declaration of
its kind.  A kind should be a globally unique name across the entire
Avocado community and users.

When choosing a Runnable ``kind`` name, it's advisable that it should
be:

 * Informative
 * Succinct
 * Unique

If a kind is thought to be generally useful to more than one user
(where a user may mean a project using Avocado), it's a good idea
to also have a generic name.  For instance, if a Runnable is going
to describe how to run native tests for the Go programming language,
its ``kind`` should probably be ``go``.

On the other hand, if a Runnable is going to be used to describe tests
that behave in a very peculiar way for a specific project, it's
probably a good idea to map its ``kind`` name to the project name.
For instance, if one is describing how to run an ``iotest`` that is
part of the ``QEMU`` project, it may be a good idea to name this kind
``qemu-iotest``.

A Runnable's ``uri``
++++++++++++++++++++

Besides a ``kind``, each runnable kind may require a different amount
of information to be provided so that it can be instantiated.

Based on the accumulated experience so far, it's expected that a
Runnable's ``uri`` is always going to be required.  Think of the URI
as the one piece of information that can uniquely distinguish the
entity (of a given ``kind``) that will be executed.

If, for instance, a given runnable describes the execution of a
executable file already present in the system, it may use its path,
say ``/bin/true``, as its ``uri`` value.  If a runnable describes a
web service endpoint, its ``uri`` value may just as well be its
network URI, such as ``https://example.org:8080``.

Runnable examples
+++++++++++++++++

Possibly the simplest example for the use of a Runnable is to describe
how to run a standalone executable, such as the ones available on your
``/bin`` directory.

As stated earlier, a runnable must declare its kind.  For standalone
executables, a name such as ``exec`` fulfills the naming suggestions
given earlier.

A Runnable can be created in a number of ways.  The first one is
through :class:`avocado.core.nrunner.Runnable`, a very low level (and
internal) API.  Still, it serves as an example::

  >>> from avocado.core.nrunner.runnable import Runnable
  >>> runnable = Runnable('exec', '/bin/true')
  >>> runnable
  <Runnable kind="exec" uri="/bin/true" config="{}" args="()" kwargs="{}" tags="None" dependencies="None" variant="None">

The second way is through a JSON based file, which, for the lack of a
better term, we're calling a (Runnable) "recipe".  The recipe file
itself will look like::

  {"kind": "exec", "uri": "/bin/true"}

And example the code to create it::

  >>> from avocado.core.nrunner.runnable import Runnable
  >>> runnable = Runnable.from_recipe("/path/to/recipe.json")
  >>> runnable
  <Runnable kind="exec" uri="/bin/true" config="{}" args="()" kwargs="{}" tags="None" dependencies="None" variant="None">

The third way to create a Runnable, is even more internal.  Its usage
is **discouraged**, unless you are creating a tool that needs to
create Runnables based on the user's input from the command line::

  >>> from avocado.core.nrunner.runnable import Runnable
  >>> runnable = Runnable.from_args({'kind': 'exec', 'uri': '/bin/true'})
  >>> runnable
  <Runnable kind="exec" uri="/bin/true" config="{}" args="()" kwargs="{}" tags="None" dependencies="None" variant="None">

Runner
~~~~~~

A Runner, within the context of the nrunner architecture, is an
active entity.  It acts on the information that a runnable contains,
and quite simply, should be able to run what the Runnable describes.

A Runner will usually be tied to a specific ``kind`` of Runnable.
That type of relationship (Runner is capable of running kind "foo"
and Runnable is of the same kind "foo") is the expected mechanism that
will be employed when selecting a Runner.

It's recommended that a runner takes the form of an executable that
follows the ``avocado-runner-$KIND`` naming pattern and conforms to a
given interface/behavior, including accepting standardized command
line arguments and producing standardized output.  This gives the
runner the highest probability of working with different spawners,
including ones that would run on isolated or remote environments.

.. tip:: for a very basic example of the interface expected, refer to
         ``selftests/functional/nrunner_interface.py`` on the
         Avocado source code tree.

A Runner can also be, at the lowest layer, a Python class that
inherits from :class:`avocado.core.nrunner.BaseRunner`, and implements
at least a matching constructor method, and a ``run()`` method that
should yield dictionary(ies) as result(s).  Avocado may support in the
future the usage of such runners directly, which can speed up
execution, but limits where those can be run to pretty much the same
machine.

Runner output
+++++++++++++

A Runner should, if possible, produce status information on the
progress of the execution of a Runnable.  While the Runner is
executing what a Runnable describes, should it produce interesting
information, the Runner should attempt to forward that along its
generated status.

For instance, using the ``exec`` Runner example, it's helpful to start
producing status that the process has been created and it's running as
soon as possible, even if no other output has been produced by the
executable itself.  These can be as simple as a sequence of::

  {"status": "started"}
  {"status": "running"}
  {"status": "running"}

When the process is finished, the Runner may return::

  {"status": "finished", "returncode": 0, 'stdout': b'', 'stderr': b''}

.. tip:: Besides the status of ``finished``, and a return code which
         can be used to determine a success or failure status, a
         Runner may not be obliged to determine the overall PASS/FAIL
         outcome.  Whoever called the runner may be responsible to
         determine its overall result, including a PASS/FAIL
         judgement.

Even though this level of information is expected to be generated by
the Runner, whoever is calling a Runner, should be prepared to receive
as little information as possible, and act accordingly.  That includes
receiving no information at all.

For instance, if a Runner fails to produce any information within a
given amount of time, it may be considered faulty and be completely
discarded.  This would probably end up being represented as a
``INTERRUPTED`` kind of status on a higher layer (say at the "Job"
layer).

Task
~~~~

A task is one specific instance/occurrence of the execution of a
runnable with its respective runner.  They should have a unique
identifier, although a task by itself won't enforce its uniqueness in
a process or any other type of collection.

A task is responsible for producing and reporting status updates.
This status updates are in a format similar to those received from a
runner, but will add more information to them, such as its unique
identifier.

A different aggregate structure,
:class:`avocado.core.task.runtime.RuntimeTask`, is used to keep track
of the extra information while the task is being run.

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

  python3 -m avocado.plugins.runners.exec_test capabilities | python -m json.tool
  {
      "runnables": [
          "exec-test"
      ],
      "commands": [
          "capabilities",
          "runnable-run",
          "runnable-run-recipe",
          "task-run",
          "task-run-recipe"
      ],
      "configuration_used": [
          "run.keep_tmp",
          "runner.exectest.exitcodes.skip"
      ]
  }

Runner scripts
--------------

Specific runners are available as ``avocado-runner-$kind``.  For
instance, the runner for ``exec-test`` is available as
``avocado-runner-exec-test``.  When using specific runners, the
``-k|--kind`` parameter can be omitted.

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

Runnables from parameters
~~~~~~~~~~~~~~~~~~~~~~~~~

You can run a "noop" runner with::

  avocado-runner-noop runnable-run -k noop

You can run an "exec" runner with::

  avocado-runner-exec-test runnable-run -k exec-test -u /bin/sleep -a 3.0

You can run an "exec-test" runner with::

  avocado-runner-exec-test runnable-run -k exec-test -u /bin/true

You can run a "python-unittest" runner with::

  avocado-runner-python-unittest runnable-run -k python-unittest -u selftests/unit/test_test.py:TestClassTestUnit.test_long_name

Runnables from recipes
~~~~~~~~~~~~~~~~~~~~~~

You can run a "noop" recipe with::

  avocado-runner-noop runnable-run-recipe examples/nrunner/recipes/runnable/noop.json

You can run an "exec-test" runner with::

  avocado-runner-exec-test runnable-run-recipe examples/nrunner/recipes/runnable/exec_test_sleep_3.json

You can run a "python-unittest" runner with::

  avocado-runner-python-unittest runnable-run-recipe examples/nrunner/recipes/runnable/python_unittest.json

Writing new runner scripts
--------------------------

Even though you can write runner scripts in any language, if you're
writing a new runner script in Python, you can benefit from the
:class:`avocado.core.nrunner.app.BaseRunnerApp` class and from the
:class:`avocado.core.nrunner.runner.BaseRunner` class.

The following is a complete example of a script that could be named
``avocado-runner-magic`` that could act as a nrunner compatible runner
for runnables with kind ``magic``.

.. literalinclude:: ../../../../../examples/plugins/tests/magic/avocado_magic/runner.py
   :language: python
   :linenos:

For a more complete explanation on the runner scripts and how they
relate to plugins, please refer to :ref:`new-test-type-plugin-example`.

Runners messages
----------------

When run as part of a job, every runner has to send information
about its execution status to the Avocado job. That information
is sent by messages which have different types based on the
information which they are transmitting.

Avocado understands three main types of messages:

* started (required)
* running
* finished (required)

The started and finished messages are obligatory and every runner has to
send those. The running messages can contain different information
during runner run-time like logs, warnings, errors .etc and that
information will be processed by the avocado core.

The messages are standard Python dictionaries with a specific structure.
You can create it by yourself based on the table :ref:`supported-message-types`,
or you can use helper methods in :class:`avocado.core.utils.messages`
which will generate them for you.

.. _supported-message-types:

Supported message types
~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: avocado.core.messages.StartMessageHandler
   :noindex:

.. autoclass:: avocado.core.messages.FinishMessageHandler
   :noindex:

Running messages
++++++++++++++++
This message can be used during the run-time and has different properties
based on the information which is being transmitted.

.. autoclass:: avocado.core.messages.LogMessageHandler
   :noindex:

.. autoclass:: avocado.core.messages.StdoutMessageHandler
   :noindex:

.. autoclass:: avocado.core.messages.StderrMessageHandler
   :noindex:

.. autoclass:: avocado.core.messages.WhiteboardMessageHandler
   :noindex:

.. autoclass:: avocado.core.messages.FileMessageHandler
   :noindex:
