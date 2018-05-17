==============
Test discovery
==============

In this section you can learn how tests are being discovered and how to affect
this process.


The order of test loaders
=========================

Avocado supports different types of test starting with `SIMPLE` tests, which
are simply executable files, then unittest-like tests called `INSTRUMENTED`
up to some tests like the `avocado-vt` ones, which uses complex
matrix of tests from config files that don't directly map to existing files.
Given the number of loaders, the mapping from test names on the command line
to executed tests might not always be unique. Additionally some people might
always (or for given run) want to execute only tests of a single type.

To adjust this behavior you can either tweak ``plugins.loaders`` in avocado
settings (``/etc/avocado/``), or temporarily using ``--loaders``
(option of ``avocado run``) option.

This option allows you to specify order and some params of the available test
loaders. You can specify either loader_name (``file``), loader_name +
TEST_TYPE (``file.SIMPLE``) and for some loaders even additional params
passed after ``:`` (``external:/bin/echo -e``. You can also supply
``@DEFAULT``, which injects into that position all the remaining unused
loaders.

To get help about ``--loaders``::

    $ avocado run --loaders ?
    $ avocado run --loaders external:?

Example of how ``--loaders`` affects the produced tests (manually gathered
as some of them result in error)::

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

Running simple tests with arguments
===================================

This used to be supported out of the box by running
``avocado run "test arg1 arg2"`` but it was quite confusing and removed.
It is still possible to achieve that by using shell and one can even combine
normal tests and the parametrized ones::

    $ avocado run --loaders file external:/bin/sh -- existing_file.py "'/bin/echo something'" nonexisting-file

This will run 3 tests, the first one is a normal test defined by
``existing_file.py`` (most probably an instrumented test). Then
we have ``/bin/echo`` which is going to be executed via
``/bin/sh -c '/bin/echo something'``. The last one would be
``nonexisting-file`` which would execute ``/bin/sh -c nonexisting-file``
which most probably fails.

Note that you are responsible for quotating the test-id (see the
``"'/bin/echo something'"`` example).

Filtering tests by tags
=======================

Avocado allows tests to be given tags, which can be used to create
test categories. With tags set, users can select a subset of the
tests found by the test resolver (also known as test loader). For
more information about the test tags, visit
`<WritingTests.html#categorizing-tests>`__

Test References
===============

A Test Reference is a string that can be resolved into (interpreted as)
one or more tests by the Avocado Test Resolver.

Each resolver (a.k.a. loader) can handle the Test References
differently. For example, External Loader will use the Test Reference as
an argument for the external command, while the File Loader will expect
a file path.

If you don't specify the loader that you want to use, all of the
available loaders will be used to resolve the provided Test References.
One by one, the Test References will be resolved by the first loader
able to create a test list out of that reference.

Below you can find some extra details about the specific builtin Avocado
loaders. For Loaders introduced to Avocado via plugins (VT, Robot, ...),
please refer to the corresponding loader/plugin documentation.

File Loader
-----------

For the File Loader, the loader responsible for discovering INSTRUMENTED,
PyUNITTEST (classic python unittests) and SIMPLE tests.

If the file corresponds to an INSTRUMENTED or PyUNITTEST test, you can filter
the Test IDs by adding to the Test Reference a ``:`` followed by a regular
expression.

For instance, if you want to list all tests that are present in the
``gdbtest.py`` file, you can use the list command below::

    $ avocado list /usr/share/doc/avocado/tests/gdbtest.py
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_start_exit
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_existing_commands_raw
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_existing_commands
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_load_set_breakpoint_run_exit_raw
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_load_set_breakpoint_run_exit
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_generate_core
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_set_multiple_break
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_disconnect_raw
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_disconnect
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_remote_exec
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_stream_messages
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_connect_multiple_clients
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_server_exit
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_multiple_servers
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_interactive
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_interactive_args
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_exit_status
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_server_stderr
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_server_stdout
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_interactive_stdout
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_remote

To filter the results, listing only the tests that have
``test_interactive`` in their test method names, you can execute::

    $ avocado list /usr/share/doc/avocado/tests/gdbtest.py:test_interactive
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_interactive
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_interactive_args
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_interactive_stdout

As the string after the ``:`` is a regular expression, three tests were
filtered in. You can manipulate the regular expression to have only the
test with that exact name::

    $ avocado list /usr/share/doc/avocado/tests/gdbtest.py:test_interactive$
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_interactive

The regular expression enables you to have more complex filters.
Example::

    $ avocado list /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_[le].*raw
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_existing_commands_raw
    INSTRUMENTED /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_load_set_breakpoint_run_exit_raw

Once the test reference is providing you the expected outcome, you can
replace the ``list`` subcommand with the ``run`` subcommand to execute your
tests::

    $ avocado run /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_[le].*raw
    JOB ID     : 333912fb02698ed5339a400b832795a80757b8af
    JOB LOG    : $HOME/avocado/job-results/job-2017-06-14T14.54-333912f/job.log
     (1/2) /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_existing_commands_raw: PASS (0.59 s)
     (2/2) /usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_load_set_breakpoint_run_exit_raw: PASS (0.42 s)
    RESULTS    : PASS 2 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 1.15 s
    JOB HTML   : $HOME/avocado/job-results/job-2017-06-14T14.54-333912f/html/results.html

.. warning:: Specially when using regular expressions, it's recommended
   to individually enclose your Test References in quotes to avoid bash
   of corrupting them. In that case, the command from the example above
   would be:
   ``avocado run "/usr/share/doc/avocado/tests/gdbtest.py:GdbTest.test_[le].*raw"``

External Loader
---------------

Using the External Loader, Avocado will consider that and External
Runner will be in place and so Avocado doesn't really need to resolve
the references. Instead, Avocado will pass the references as parameters
to the External Runner. Example::

    $ avocado run 20
    Unable to resolve reference(s) '20' with plugins(s) 'file', 'robot',
    'vt', 'external', try running 'avocado list -V 20' to see the details.

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
