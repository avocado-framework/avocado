Avocado Data Directories
========================

When running tests, we are frequently looking to:

* Locate tests
* Write logs to a given location
* Grab files that will be useful for tests, such as ISO files or VM disk
  images

Avocado has a module dedicated to finding those paths, to avoid cumbersome path
manipulation magic that people had to do in previous test frameworks [#f1]_.

If you want to list all relevant directories for your test, you can use
`avocado config --datadir` command to list those directories. Executing
it will give you an output similar to the one seen below::

    $ avocado config --datadir
    Config files read (in order):
        * /etc/avocado/avocado.conf
        * /etc/avocado/conf.d/resultsdb.conf
        * /etc/avocado/conf.d/result_upload.conf
        * /etc/avocado/conf.d/jobscripts.conf
        * /etc/avocado/conf.d/gdb.conf
          $HOME/.config/avocado/avocado.conf

    Avocado replaces config dirs that can't be accessed
    with sensible defaults. Please edit your local config
    file to customize values.

    Avocado Data Directories:
        base  $HOME/avocado
        tests $HOME/Code/avocado/examples/tests
        data  $HOME/avocado/data
        logs  $HOME/avocado/job-results

Note that, while Avocado will do its best to use the config values you
provide in the config file, if it can't write values to the locations
provided, it will fall back to (we hope) reasonable defaults, and we
notify the user about that in the output of the command.

The relevant API documentation and meaning of each of those data directories is
in :mod:`avocado.core.data_dir`, so it's highly recommended you take a look.

You may set your preferred data dirs by setting them in the Avocado config files.
The only exception for important data dirs here is the Avocado tmp dir, used to
place temporary files used by tests. That directory will be in normal circumstances
`/var/tmp/avocado_XXXXX`, (where `XXXXX` is in actuality a random string) securely
created on `/var/tmp/`, unless the user has the `$TMPDIR` environment variable set,
since that is customary among unix programs.

The next section of the documentation explains how you can see and set config
values that modify the behavior for the Avocado utilities and plugins.

.. [#f1] For example, autotest.
