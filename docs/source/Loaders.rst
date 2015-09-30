==============
Test discovery
==============

In this section you can learn how tests are being discovered and how to affect
this process.


The order of test loaders
=========================

Avocado supports different types of test starting with `SIMPLE` tests, which
are simply executable files, then unittest-like tests called `INSTRUMENTED`
up to some fancy tests like `avocado-vt` (extra plugin), which uses complex
matrix of tests from config files completely unrelated to existing files.
Given the number of loaders, the mapping from test names on the command line
to executed tests might not always be unique. Additionally some people might
always (or for given run) want to execute only tests of a single type.

To adjust this behavior you can either tweak ``plugins.loaders`` in avocado
settings (``/etc/avocado/``), or temporarily using ``--loaders``
(option of ``avocado run``) option.

This option allows you to specify order and some params of the available test
loaders. You can specify either ``@`` + loader_name (``@file``),
TEST_TYPE (``SIMPLE``) and for some loaders even additional params passed
after ``:`` (``@file:/bin/echo -e`` or ``INNER_RUNNER:/bin/echo -e``). You can
also supply ``DEFAULT``, which injects into that position all the remaining
unused loaders.

Examples which lists what tests would be executed with various options
(with avocado-vt installed)::

    $ avocado run passtest boot this_does_not_exists /bin/echo
        > INSTRUMENTED passtest.py:PassTest.test
        > VT           io-github-autotest-qemu.boot
        > MISSING      this_does_not_exists
        > SIMPLE       /bin/echo
    $ avocado run passtest boot this_does_not_exists /bin/echo --loaders DEFAULT "@file:/bin/echo -e"
        > INSTRUMENTED passtest.py:PassTest.test
        > VT           io-github-autotest-qemu.boot
        > INNER_RUNNER this_does_not_exists
        > SIMPLE       /bin/echo
    $ avocado run passtest boot this_does_not_exists /bin/echo --loaders SIMPLE INSTRUMENTED DEFAULT INNER_RUNNER:/bin/echo
        > INSTRUMENTED passtest.py:PassTest.test
        > VT           io-github-autotest-qemu.boot
        > INNER_RUNNER this_does_not_exists
        > SIMPLE       /bin/echo

