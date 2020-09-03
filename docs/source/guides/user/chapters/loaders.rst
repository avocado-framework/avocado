.. _test-loaders:

Understanding the test discovery (Avocado Loaders)
==================================================

In this section you can learn how tests are being discovered and how to
customize this process.

.. note:: Some definitions here may be out of date. The current runner can
   still be using some of these definitions in its design, however, we are
   working on an improved version of the runner, the NextRunner that will use
   an alternative strategy.

Test Loaders
------------

A Test Loader is an Avocado component that is responsible for
discovering tests that Avocado can run.  In the process, Avocado
gathers enough information to allow the test to be run.  Additionally,
Avocado collects extra information available within the test, such as
tags that can be used to filter out tests from actual execution.

This whole process is, unless otherwise stated or manually configured,
safe, in the sense that no test code will be executed.

How Loaders discover tests
--------------------------

Avocado will apply ordering to the discovery process, so loaders that
run earlier, will have higher precedence in discovering tests.

A loader implementation is free to implement whatever logic it needs
to discover tests.  The important fact about how a loader discover
tests is that it should return one or more "test factory", an internal
data structure that, as stated before, contains enough information to
allow the test to be executed.

The order of test loaders
-------------------------

As described in previous sections, Avocado supports different types of test
starting with `SIMPLE` tests, which are simply executable files, the basic
Python unittest and tests called `INSTRUMENTED`.

With additional plugins new test types can be supported, like the `avocado-vt`
ones, which uses complex matrix of tests from config files that don't directly
map to existing files.

Given the number of loaders, the mapping from test names on the command line to
executed tests might not always be unique.  Additionally some people might
always (or for given run) want to execute only tests of a single type.

To adjust this behavior you can either tweak ``plugins.loaders`` in avocado
settings (``/etc/avocado/``), or temporarily using ``--loaders`` (option of
``avocado run``) option.

This option allows you to specify order and some params of the available test
loaders. You can specify either loader_name (``file``), loader_name + TEST_TYPE
(``file.SIMPLE``) and for some loaders even additional params passed after
``:`` (``external:/bin/echo -e``. You can also supply ``@DEFAULT``, which
injects into that position all the remaining unused loaders.

Example of how ``--loaders`` affects the produced tests (manually gathered as
some of them result in error)::

    $ avocado run passtest.py boot this_does_not_exist /bin/echo
        > INSTRUMENTED passtest.py:PassTest.test
        > VT           io-github-autotest-qemu.boot
        > MISSING      this_does_not_exist
        > SIMPLE       /bin/echo
    $ avocado run passtest.py boot this_does_not_exist /bin/echo --loaders @DEFAULT "external:/bin/echo -e"
        > INSTRUMENTED passtest.py:PassTest.test
        > VT           io-github-autotest-qemu.boot
        > EXTERNAL     this_does_not_exist
        > SIMPLE       /bin/echo
    $ avocado run passtest.py boot this_does_not_exist /bin/echo --loaders file.SIMPLE file.INSTRUMENTED @DEFAULT external.EXTERNAL:/bin/echo
        > INSTRUMENTED passtest.py:PassTest.test
        > VT           io-github-autotest-qemu.boot
        > EXTERNAL     this_does_not_exist
        > SIMPLE       /bin/echo

Test References
~~~~~~~~~~~~~~~

A Test Reference is a string that can be resolved into (interpreted as) one or
more tests by the Avocado Test Resolver.

Each resolver (a.k.a. loader) can handle the Test References differently. For
example, External Loader will use the Test Reference as an argument for the
external command, while the File Loader will expect a file path.

If you don't specify the loader that you want to use, all of the available
loaders will be used to resolve the provided Test References.  One by one, the
Test References will be resolved by the first loader able to create a test list
out of that reference.

Basic Avocado Loaders
---------------------

Below you can find some extra details about the specific builtin Avocado
loaders. For Loaders introduced to Avocado via plugins (VT, Robot, ...), please
refer to the corresponding loader/plugin documentation.


File Loader
~~~~~~~~~~~

For the File Loader, the loader responsible for discovering INSTRUMENTED,
PyUNITTEST (classic python unittests) and SIMPLE tests.

If the file corresponds to an INSTRUMENTED or PyUNITTEST test, you can filter
the Test IDs by adding to the Test Reference a ``:`` followed by a regular
expression.

For instance, if you want to list all tests that are present in the
``gdbtest.py`` file, you can use the list command below::

    $ avocado list examples/tests/gdbtest.py
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_start_exit
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_existing_commands_raw
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_existing_commands
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_load_set_breakpoint_run_exit_raw
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_load_set_breakpoint_run_exit
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_generate_core
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_set_multiple_break
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_disconnect_raw
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_disconnect
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_remote_exec
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_stream_messages
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_connect_multiple_clients
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_server_exit
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_multiple_servers
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_server_stderr
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_server_stdout
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_remote

To filter the results, listing only the tests that have ``test_disconnect`` in
their test method names, you can execute::

    $ avocado list examples/tests/gdbtest.py:test_disconnect
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_disconnect_raw
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_disconnect

As the string after the ``:`` is a regular expression, two tests were
filtered in. You can manipulate the regular expression to have only the
test with that exact name::

    $ avocado list examples/tests/gdbtest.py:test_disconnect$
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_disconnect

The regular expression enables you to have more complex filters.
Example::

    $ avocado list examples/tests/gdbtest.py:GdbTest.test_[le].*raw
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_existing_commands_raw
    INSTRUMENTED examples/tests/gdbtest.py:GdbTest.test_load_set_breakpoint_run_exit_raw

Once the test reference is providing you the expected outcome, you can
replace the ``list`` subcommand with the ``run`` subcommand to execute your
tests::

    $ avocado run examples/tests/gdbtest.py:GdbTest.test_[le].*raw
    JOB ID     : 333912fb02698ed5339a400b832795a80757b8af
    JOB LOG    : $HOME/avocado/job-results/job-2017-06-14T14.54-333912f/job.log
     (1/2) examples/tests/gdbtest.py:GdbTest.test_existing_commands_raw: PASS (0.59 s)
     (2/2) examples/tests/gdbtest.py:GdbTest.test_load_set_breakpoint_run_exit_raw: PASS (0.42 s)
    RESULTS    : PASS 2 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 1.15 s
    JOB HTML   : $HOME/avocado/job-results/job-2017-06-14T14.54-333912f/html/results.html

.. warning:: Specially when using regular expressions, it's recommended
   to individually enclose your Test References in quotes to avoid bash
   of corrupting them. In that case, the command from the example above
   would be:
   ``avocado run "examples/tests/gdbtest.py:GdbTest.test_[le].*raw"``

External Loader
~~~~~~~~~~~~~~~

Using the External Loader, Avocado will consider that and External Runner will
be in place and so Avocado doesn't really need to resolve the references.
Instead, Avocado will pass the references as parameters to the External Runner.
Example::

    $ avocado run 20
    Unable to resolve reference(s) '20' with plugins(s) 'file', 'robot',
    'vt', 'external', try running 'avocado -V list 20' to see the details.

In the command above, no loaders can resolve ``20`` as a test. But running
the command above with the External Runner ``/bin/sleep`` will make Avocado
to actually execute ``/bin/sleep 20`` and check for its return code::

    $ avocado run 20 --loaders external:/bin/sleep
    JOB ID     : 42215ece2894134fb9379ee564aa00f1d1d6cb91
    JOB LOG    : $HOME/avocado/job-results/job-2017-06-19T11.17-42215ec/job.log
     (1/1) 20: PASS (20.03 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 20.13 s
    JOB HTML   : $HOME/avocado/job-results/job-2017-06-19T11.17-42215ec/html/results.html

.. warning:: It's safer to put your Test References at the end of the
   command line, after a `--`. That will avoid argument vs. Test
   References clashes. In that case, everything after the `--` will
   be considered positional arguments, therefore Test References.
   Considering that syntax, the command for the example above would be:
   ``avocado run --loaders external:/bin/sleep -- 20``

TAP Loader
~~~~~~~~~~

This loader enables Avocado to execute binaries or scripts and parse
their `Test Anything Protocol <https://testanything.org>`_ output.

The tests can be run as usual::

    $ avocado run --loaders tap -- ./mytaptest

Notice that you have to be explicit about the test loader you're
using, otherwise, since the test files are executable binaries, the
``FileLoader`` will detect the file as a ``SIMPLE`` test, making the
whole test suite to be executed as one test only from the Avocado
perspective.  Because TAP test programs should exit with a zero exit
status, this will cause the test to pass even if there are failures.
