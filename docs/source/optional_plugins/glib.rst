.. _glib-plugin:

===========
GLib Plugin
===========

This optional plugin enables Avocado to list and run tests written using the
`GLib Test Framework <https://developer.gnome.org/glib/stable/glib-Testing.html>`_.

To list the tests, just provide the test file path::

    $ avocado list --loaders glib -- tests/check-qnum
    GLIB tests/check-qnum:/qnum/from_int
    GLIB tests/check-qnum:/qnum/from_uint
    GLIB tests/check-qnum:/qnum/from_double
    GLIB tests/check-qnum:/qnum/from_int64
    GLIB tests/check-qnum:/qnum/get_int
    GLIB tests/check-qnum:/qnum/get_uint
    GLIB tests/check-qnum:/qnum/to_qnum
    GLIB tests/check-qnum:/qnum/to_string

Notice that you have to be explicit about the test loader you're using,
otherwise, since the test files are executable binaries, the FileLoader will
report the file as a SIMPLE test, making the whole test suite to be executed
as one test only from the Avocado perspective.

The Avocado test reference syntax to filter the tests you want to
execute is also available in this plugin::

    $ avocado list --loaders glib -- tests/check-qnum:int
    GLIB tests/check-qnum:/qnum/from_int
    GLIB tests/check-qnum:/qnum/from_uint
    GLIB tests/check-qnum:/qnum/from_int64
    GLIB tests/check-qnum:/qnum/get_int
    GLIB tests/check-qnum:/qnum/get_uint

To run the tests, just switch from `list` to `run`::

    $ avocado run --loaders glib -- tests/check-qnum:int
    JOB ID     : 380a2b3d65b3fce9f8062d84f8635712d6e03133
    JOB LOG    : $HOME/avocado/job-results/job-2018-02-23T18.02-380a2b3/job.log
     (1/5) tests/check-qnum:/qnum/from_int: PASS (0.03 s)
     (2/5) tests/check-qnum:/qnum/from_uint: PASS (0.03 s)
     (3/5) tests/check-qnum:/qnum/from_int64: PASS (0.04 s)
     (4/5) tests/check-qnum:/qnum/get_int: PASS (0.03 s)
     (5/5) tests/check-qnum:/qnum/get_uint: PASS (0.03 s)
    RESULTS    : PASS 5 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 0.46 s
    JOB HTML   : $HOME/avocado/job-results/job-2018-02-23T18.02-380a2b3/results.html
