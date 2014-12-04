========================
Avocado Data Directories
========================

When running tests, we are frequently looking to:

* Locate tests
* Write logs to a given location
* Grab files that will be useful for tests, such as ISO files or VM disk
  images

Avocado has a module dedicated to find those paths, to avoid cumbersome
path manipulation magic that people had to do in previous test frameworks [1].

If you want to list all relevant directories for your test, there's a builtin
avocado plugin called ``datadir`` to do that. You can run::

    $ avocado datadir
    Avocado Data Directories:
        base dir:        /home/lmr/avocado
        tests dir:       /home/lmr/avocado/tests
        data dir:        /home/lmr/avocado/data
        logs dir:        /home/lmr/avocado/logs
        tmp dir:         /tmp/avocado

The relevant API documentation and meaning of each of those data directories
is in :mod:`avocado.core.data_dir`, so it's higly recommended you take a look.

You may set your preferred data dirs by setting them in the avocado config files.
The next section of the documentation explains how you can see and set config
values that modify the behavior for the avocado utilities and plugins.

[1] For example, autotest.