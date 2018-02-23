.. _gtester-plugin:

==============
Gtester Plugin
==============

This optional plugin enables Avocado to list and run tests written using the
`GLib Test Framework <https://developer.gnome.org/glib/stable/glib-Testing.html>`_
with the `Gtester test runner <https://developer.gnome.org/glib/stable/gtester.html>`_.

The `Gtester test runner <https://developer.gnome.org/glib/stable/gtester.html>`_
is included in the GLib Devel package.

After installed, you can list/run tests providing the test file path::

    ~$ avocado list --loaders gtester -- tests/bios-tables-test
    GTESTER tests/bios-tables-test:/x86_64/acpi/piix4
    GTESTER tests/bios-tables-test:/x86_64/acpi/q35
    GTESTER tests/bios-tables-test:/x86_64/acpi/piix4/bridge
    GTESTER tests/bios-tables-test:/x86_64/acpi/piix4/ipmi
    GTESTER tests/bios-tables-test:/x86_64/acpi/piix4/cpuhp
    GTESTER tests/bios-tables-test:/x86_64/acpi/piix4/memhp
    GTESTER tests/bios-tables-test:/x86_64/acpi/q35/bridge
    GTESTER tests/bios-tables-test:/x86_64/acpi/q35/ipmi
    GTESTER tests/bios-tables-test:/x86_64/acpi/q35/cpuhp
    GTESTER tests/bios-tables-test:/x86_64/acpi/q35/memhp

Notice that you have to be explicit about the test loader you're using,
otherwise, since the test files are executable binaries, the FileLoader will
report the file as a SIMPLE test, making the whole test suite to be executed
as one test only from the Avocado perspective.

The Avocado test reference syntax to filter the tests you want to
execute is also available in this plugin::

    ~$ avocado list --loaders gtester -- tests/bios-tables-test:q35
    GTESTER tests/bios-tables-test:/x86_64/acpi/q35
    GTESTER tests/bios-tables-test:/x86_64/acpi/q35/bridge
    GTESTER tests/bios-tables-test:/x86_64/acpi/q35/ipmi
    GTESTER tests/bios-tables-test:/x86_64/acpi/q35/cpuhp
    GTESTER tests/bios-tables-test:/x86_64/acpi/q35/memhp

To run the tests, just switch from `list` to `run`::

    $ avocado run --loaders gtester -- tests/bios-tables-test:q35
    JOB ID     : 72a59f2c68f2e25bb9c112864a5fa9c46b15b864
    JOB LOG    : $HOME/avocado/job-results/job-2018-02-20T13.54-72a59f2/job.log
     (1/5) tests/bios-tables-test:/x86_64/acpi/q35: PASS (2.72 s)
     (2/5) tests/bios-tables-test:/x86_64/acpi/q35/bridge: PASS (0.58 s)
     (3/5) tests/bios-tables-test:/x86_64/acpi/q35/ipmi: PASS (0.56 s)
     (4/5) tests/bios-tables-test:/x86_64/acpi/q35/cpuhp: PASS (0.58 s)
     (5/5) tests/bios-tables-test:/x86_64/acpi/q35/memhp: PASS (0.58 s)
    RESULTS    : PASS 5 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 5.28 s
    JOB HTML   : $HOME/avocado/job-results/job-2018-02-20T13.54-72a59f2/results.html

