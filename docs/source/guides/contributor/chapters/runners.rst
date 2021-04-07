.. _nrunner:

The "nrunner" and "runner" test runner
======================================

This section details a test runner called "nrunner", also known as
N(ext) Runner, and the architecture around.  It compares it with the
older (and default) test runner, simply called "runner".

At its essence, this new architecture is about making Avocado more
capable and flexible, and even though it starts with a major internal
paradigm change within the test runner, it will also affect users and
test writers.

The :mod:`avocado.core.nrunner` module was initially responsible for
most of the N(ext)Runner code, but as development continues, it's
spreading around to other places in the Avocado source tree.  Other
components with different and seemingly unrelated names, say the
"resolvers" or the "spawners", are also pretty much about the
N(ext)Runner and are not used in the current (default) architecture.

Motivation
----------

There are a number of reasons for introducing a different architecture
and implementation.  Some of them are related to limitations found in
the current implementation, that were found to be too hard to remove
without major breakage.  Also, missing features that are deemed
important would be a better fit wihin a different architecture.

For instance, these are the current limitations of the Avocado test
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

Current and N(ext) Runner components of Avocado
-----------------------------------------------

Whenever we mention the **current** architecture or implementation,
we are talking about:

* ``avocado list`` command
* ``avocado run`` command
* :mod:`avocado.core.loader` module to find tests

Whenever we talk about the N(ext)Runner, we are talking about:

* ``avocado list --resolver`` command
* ``avocado run --test-runner=nrunner`` command
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

Finding tests
~~~~~~~~~~~~~

The first thing Avocado needs to do, before actually running any
tests, is translating the "names" given as arguments to ``avocado run``
into actual tests.  Even though those names will usually be file names,
this is not a requirement.  Avocado calls those "names" given as arguments
to ``avocado run`` "test references", because they are references that
hopefully "point to" tests.

Here we need to make a distincion between the current architecture,
and the architecture which the N(ext)Runner introduces.  In the
current Avocado test runner, this process happens by means of the
:mod:`avocado.core.loader` module.  The very same mechanism, is used
when listing tests.  This produces an internal representation of
the tests, which we simply call a "factory"::

  +--------------------+    +---------------------+
  | avocado list | run | -> | avocado.core.loader | ---+
  +--------------------+    +---------------------+    |
                                                       |
    +--------------------------------------------------+
    |
    v
  +--------------------------------------+
  | Test Factory 1                       |
  +--------------------------------------+
  | Class: TestFoo                       |
  | Parameters:                          |
  |  - modulePath: /path/to/module.py    |
  |  - methodName: test_foo              |
  |  ...                                 |
  +--------------------------------------+

  +--------------------------------------+
  | Test Factory 2                       |
  +--------------------------------------+
  | Class: TestBar                       |
  | Parameters:                          |
  |  - modulePath: /path/to/module.py    |
  |  - methodName: test_bar              |
  |  ...                                 |
  +--------------------------------------+

  ...

Because the N(ext)Runner is living side by side with the current
architecture, command line options have been introduced to distinguish
between them: ``avocado list --resolver`` and ``avocado
run --test-runner=nrunner``.

On the N(ext)Runner architecture, a different terminology and
foundation is used.  Each one of the test references given to ``list
--resolver`` or ``run --test-runner=runner`` will be "resolved" into
zero or more tests.  Being more precise and verbose, resolver plugins
will produce :class:`avocado.core.resolver.ReferenceResolution`, which
contain zero or more :class:`avocado.core.nrunner.Runnable`, which are
described in the following section.  Overall, the process looks like::

  +-------------------------+    +-----------------------+
  | avocado list --resolver | -> | avocado.core.resolver | ---+
  +-------------------------+    +-----------------------+    |
                                                              |
    +---------------------------------------------------------+
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

The current Avocado architecture uses the "Test Factories" described
earlier to load and execute such a "code payload".  Each of those test
factories contain the name of a Python class to be instantiated, and a
number of arguments that will be given to that class initialization.

So the primary "code payload" for every Avocado test in the current
architecture will always be Python code that inherits from
:class:`avocado.core.test.Test`.  Even when the user wants to run a
standalone executable (a ``SIMPLE`` test in the current architecture
terminology), that still means loading and instantiating (effectively
executing) the Python class' :class:`avocado.core.test.SimpleTest`
code.

Once all the test factories are found by :mod:`avocado.core.loader`,
as described in the previous section, the current architecture runs
tests roughly following these steps:

1. Create one (and only one) queue to communicate with the test
   **processes**
2. For each test factory found by the loader:

  a. Unpack the test factory into a test class and its parameters,
     that is, ``test_class, parameters = test_factory``
  b. Instantiate a new **process** for the test
  c. Within the new process, instantiate the Python class, that is,
     ``test = test_class(**parameters)``
  d. Give the test access to queue, that is
     ``test.set_runner_queue(queue)``
  e. Monitor the queue and the test process until it finishes or needs
     to be terminated.

Having to describe the "Test factory" as Python classes and its
parameters, besides increasing the complexity for new types of tests,
severely limits or prevents some of goals for the N(ext)Runner
architecture listed earlier.  It should be clear that:

1. one unique queue makes communicating with multiple tests at the
   same time hard
2. test factories contain a Python class (**code**) that will be
   instantiated in the new process
3. to instantiate Python classes in other systems would require
   serializing them, which is error prone (AKA pickling nightmares)
4. the execution of tests depends on the previous point, so running
   tests in a local process is tightly coupled and hard coded into the
   test execution code

Now let's shift our attention to the N(ext)Runner architecture.  In
the N(ext)Runner architecture, a
:class:`avocado.core.nrunner.Runnable` describe a "code payload" that
will be executed, but they are not executable code themselves.
Because they are **data** and not **code**, they are easily serialized
and transported to different environments.  Running the payload
described by a ``Runnable`` is delegated to another component.

Most often, this component is a standalone executable (see
:data:`avocado.core.spawners.common.SpawnMethod.STANDALONE_EXECUTABLE`)
compatible with a specific command line interface.  The most important
interfaces such scripts must implement are the ``runnable-run`` and
``task-run`` interfaces.

Once all the ``Runnable(s)`` (within the ``ReferenceResolution(s)``)
are created by :mod:`avocado.core.resolver`, the ``avocado
run --test-runner=nrunner`` implementation follows roughly the
following steps:

1. Creates a status server that binds to a TCP port and waits for
   status messages from any number of clients
2. Creates the chosen :class:`Spawner
   <avocado.core.spawners.common.BaseSpawner>`, with
   :class:`ProcessSpawner
   <avocado.core.spawners.process.ProcessSpawner>` being the default
3. For each :class:`avocado.core.nrunner.Runnable` found by the
   resolver, turns it into a :class:`avocado.core.nrunner.Task`, which
   means giving it the following extra information:

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
test. Other Avocado subsystems, such as ``sysinfo``, could very well
leverage the same concept to describe say, commands to be executed.

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

  >>> from avocado.core import nrunner
  >>> runnable = nrunner.Runnable('exec', '/bin/true')
  >>> runnable
  <Runnable kind="exec" uri="/bin/true" args="()" kwargs="{}" tags="None" requirements="None">

The second way is through a JSON based file, which, for the lack of a
better term, we're calling a (Runnable) "recipe".  The recipe file
itself will look like::

  {"kind": "exec", "uri": "/bin/true"}

And example the code to create it::

  >>> from avocado.core import nrunner
  >>> runnable = nrunner.Runnable.from_recipe("/path/to/recipe.json")
  >>> runnable
  <Runnable kind="exec" uri="/bin/true" args="()" kwargs="{}" tags="None" requirements="None">>

The third way to create a Runnable, is even more internal.  Its usage
is **discouraged**, unless you are creating a tool that needs to
create Runnables based on the user's input from the command line::

  >>> from avocado.core import nrunner
  >>> runnable = nrunner.Runnable.from_args({'kind': 'exec', 'uri': '/bin/true'})
  >>> runnable
  <Runnable kind="exec" uri="/bin/true" args="()" kwargs="{}" tags="None" requirements="None">>

Runner
~~~~~~

A Runner, within the context of the N(ext)Runner architecture, is an
active entity.  It acts on the information that a runnable contains,
and quite simply, should be able to run what the Runnable describes.

A Runner will usually be tied to a specific ``kind`` of Runnable.
That type of relationship (Runner is capable of running kind "foo"
and Runnable is of the same kind "foo") is the expected mechanism that
will be employed when selecting a Runner.

A Runner can take different forms, depending on which layer one is
interacting with.  At the lowest layer, a Runner may be a Python class
that inherits from :class:`avocado.core.nrunner.BaseRunner`, and
implements at least a matching constructor method, and a ``run()``
method that should yield dictionary(ies) as result(s).

At a different level, a runner can take the form of an executable that
follows the ``avocado-runner-$KIND`` naming pattern and conforms to a
given interface/behavior, including accepting standardized command
line arguments and producing standardized output.

.. tip:: for a very basic example of the interface expected, refer to
         ``selftests/functional/test_nrunner_interface.py`` on the
         Avocado source code tree.

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
``TIMED_OUT`` kind of status on a higher layer (say at the "Job"
layer).

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
  {"runnables": ["noop", "exec", "exec-test", "python-unittest"],
   "commands": ["capabilities", "runnable-run", "runnable-run-recipe",
   "task-run", "task-run-recipe"]}

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

Runnables from parameters
~~~~~~~~~~~~~~~~~~~~~~~~~

You can run a "noop" runner with::

  avocado-runner runnable-run -k noop

You can run an "exec" runner with::

  avocado-runner runnable-run -k exec -u /bin/sleep -a 3.0

You can run an "exec-test" runner with::

  avocado-runner runnable-run -k exec-test -u /bin/true

You can run a "python-unittest" runner with::

  avocado-runner runnable-run -k python-unittest -u unittest.TestCase

Runnables from recipes
~~~~~~~~~~~~~~~~~~~~~~

You can run a "noop" recipe with::

  avocado-runner runnable-run-recipe examples/nrunner/recipes/runnables/noop.json

You can run an "exec" runner with::

  avocado-runner runnable-run-recipe examples/nrunner/recipes/runnables/exec_sleep_3.json

You can run a "python-unittest" runner with::

  avocado-runner runnable-run-recipe examples/nrunner/recipes/runnables/python_unittest.json

Writing new runner scripts
--------------------------

Even though you can write runner scripts in any language, if you're
writing a new runner script in Python, you can benefit from the
:class:`avocado.core.nrunner.BaseRunnerApp` class and from the
:class:`avocado.core.nrunner.BaseRunner` class.

The following is a complete example of a script that could be named
``avocado-runner-foo`` that could act as a nrunner compatible runner
for runnables with kind ``foo``.

.. literalinclude:: ../../../../../examples/nrunner/runners/avocado-runner-foo
   :language: python
   :linenos:


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

Supported message types
~~~~~~~~~~~~~~~~~~~~~~~

Started message
+++++++++++++
This message has to be sent when the runner starts the test.

:param status: 'started'
:param time: start time of the test
:type time: float
:example: {'status': 'started', 'time': 16444.819830573}

Finished message
++++++++++++++++
This message has to be sent when the runner finishes the test.

:param status: 'finished'
:param result: test result
:type result: Lowercase values for the statuses defined in :data:`avocado.core.teststatus.STATUSES`
:param time: end time of the test
:type time: float
:example: {'status': 'finished', 'result': 'pass', 'time': 16444.819830573}

Running messages
++++++++++++++++
This message can be used during the run-time and has different properties
based on the information which is being transmitted.

Log message
***********
It will save the log to the debug.log file in the task directory.

:param status: 'running'
:param type: 'log'
:param log: log message
:type log: string
:param time: Time stamp of the message
:type time: float
:example: {'status': 'running', 'type': 'log', 'log': 'log message',
         'time': 18405.55351474}

Stdout message
**************
It will save the stdout to the stdout file in the task directory.

:param status: 'running'
:param type: 'stdout'
:param log: stdout message
:type log: string
:param time: Time stamp of the message
:type time: float
:example: {'status': 'running', 'type': 'stdout', 'log': 'stdout message',
         'time': 18405.55351474}

Stderr message
**************
It will save the stderr to the stderr file in the task directory.

:param status: 'running'
:param type: 'stderr'
:param log: stderr message
:type log: string
:param time: Time stamp of the message
:type time: float
:example: {'status': 'running', 'type': 'stderr', 'log': 'stderr message',
         'time': 18405.55351474}

Whiteboard message
******************
It will save the stderr to the whiteboard file in the task directory.

:param status: 'running'
:param type: 'whiteboard'
:param log: whiteboard message
:type log: string
:param time: Time stamp of the message
:type time: float
:example: {'status': 'running', 'type': 'whiteboard',
         'log': 'whiteboard message', 'time': 18405.55351474}
