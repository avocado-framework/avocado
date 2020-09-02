Configuring
===========

.. warning:: Please, keep in mind that we are doing a significant refactoring
  on settings to have consistency when using Avocado. Some options are changing
  soon.

Avocado utilities have a certain default behavior based on educated, reasonable
(we hope) guesses about how users like to use their systems. Of course,
different people will have different needs and/or dislike our defaults, and
that's why a configuration system is in place to help with those cases

The Avocado config file format is based on the (informal) `INI`_ file
specification, that is implemented by Python's  :mod:`configparser`. The format
is simple and straightforward, composed by `sections`, that contain a number of
`keys` and `values`. Take for example a basic Avocado config file:

.. code-block:: ini

    [datadir.paths]
    base_dir = /var/lib/avocado
    test_dir = /usr/share/doc/avocado/tests
    data_dir = /var/lib/avocado/data
    logs_dir = ~/avocado/job-results

The ``datadir.paths`` section contains a number of keys, all of them related to
directories used by the test runner. The ``base_dir`` is the base directory to
other important Avocado directories, such as log, data and test directories.
You can also choose to set those other important directories by means of the
variables ``test_dir``, ``data_dir`` and ``logs_dir``. You can do this by
simply editing the config files available.

Config file parsing order
-------------------------

Avocado starts by parsing what it calls system wide config file, that is
shipped to all Avocado users on a system wide directory,
``/etc/avocado/avocado.conf`` (when installed by your distro's package
manager).

There is another directory that will be scanned by extra config files,
``/etc/avocado/conf.d``. This directory may contain plugin config files, and
extra additional config files that the system administrator/avocado developers
might judge necessary to put there.

Then it'll verify if there's a local user config file, that is located usually
in ``~/.config/avocado/avocado.conf``. The order of the parsing matters, so the
system wide file is parsed, then the user config file is parsed last, so that
the user can override values at will.

The order of files described in this section is only valid if Avocado was
installed in the system. For people using Avocado from git repos (usually
Avocado developers), that did not install it in the system, keep in mind that
Avocado will read the config files present in the git repos, and will ignore
the system wide config files. Running ``avocado config`` will let you know
which files are actually being used.

Configuring via command-line
----------------------------

Besides the configuration files, the most used features can also be configured
by command-line arguments.  For instance, regardless what you have on your
configuration files, you can disable sysinfo logging by running:

.. code-block:: shell

   $ avocado run --disable-sysinfo /bin/true


So, command-line options always will have the highest precedence during the
configuration parsing. Use this if you would like to change some behavior on
just one or a few specific executions.

Parsing order recap
-------------------

So the file parsing order is:

  * ``/etc/avocado/avocado.conf``
  * ``/etc/avocado/conf.d/*.conf``
  * ``avocado.plugins.settings`` plugins (but they can insert to any location)

        - For more information about this, visit the "Contributor's Guide"
          section named "Writing an Avocado plugin"

  * ``~/.config/avocado/avocado.conf``

You can see the actual set of files/location by using ``avocado config`` which
uses ``*`` to mark existing and used files::

   $ avocado config
   Config files read (in order, '*' means the file exists and had been read):
    * /etc/avocado/avocado.conf
    * /etc/avocado/conf.d/resultsdb.conf
    * /etc/avocado/conf.d/result_upload.conf
    * /etc/avocado/conf.d/jobscripts.conf
    * /etc/avocado/conf.d/gdb.conf
    * /etc/avocado_vt/conf.d/vt.conf
    * /etc/avocado_vt/conf.d/vt_joblock.conf
      $HOME/.config/avocado/avocado.conf

    Section.Key                              Value
    datadir.paths.base_dir                   /var/lib/avocado
    datadir.paths.test_dir                   /usr/share/doc/avocado/tests
    ...

Where the lower config files override values of the upper files and the
``$HOME/.config/avocado/avocado.conf`` file missing.

.. note::  Please note that if Avocado is running from git repos, those files
  will be ignored in favor of in tree configuration files. This is something that
  would normally only affect people developing avocado, and if you are in doubt,
  ``avocado config`` will tell you exactly which files are being used in any
  given situation.

.. note::  When Avocado runs inside virtualenv than path for global config
  files is also changed. For example, `avocado.conf` comes from the virual-env
  path `venv/etc/avocado/avocado.conf`.


Order of precedence for values used in tests
--------------------------------------------

Since you can use the config system to alter behavior and values used in tests
(think paths to test programs, for example), we established the following order
of precedence for variables (from least precedence to most):

  * default value (from library or test code)
  * global config file
  * local (user) config file
  * command line switch
  * test parameters

So the least important value comes from the library or test code default, going
all the way up to the test parameters system.

Supported data types when configuring Avocado
---------------------------------------------

As already said before, Avocado allows users to use both: configuration files
and command-line options to configure its behavior. It is important to have a
very well defined system type for the configuration file and argument options.

Although config files options and command-line arguments are always considered
``strings``, you should give a proper format representation so those values can
be parsed into a proper type internally on Avocado.

Currently Avocado supports the following data types for the configuration options:
``string``, ``integer``, ``float``, ``bool`` and ``list``. Besides those
primitive data types Avocado also supports custom data types that can be used
by a particular plugin.

Bellow, you will find information on how to set options based on those basic
data types using both: configuration files and command-line arguments.

Strings
~~~~~~~

Strings are the basic ones and the syntax is the same in both configuration
files and command-line arguments: Just the string that can be inside ``""`` or
``''``.

Example using the configuration file:

.. code-block:: ini

  [foo]
  bar = 'hello world'

String and all following types could be used with or without quotes but using
quotes for strings is important on the command line to safely handle empty
spaces and distinguish it from a list type. Therefore, the following example
will also be well handled:

.. code-block:: ini

  [foo]
  bar = hello world

Example using the command-line:

.. code-block:: bash

  $ avocado run --foo bar /bin/true

Integers
~~~~~~~~

Integer numbers are as simple as strings.

Example using the configuration file:

.. code-block:: ini

  [run]
  job_timeout = 60

Example using the command-line:

.. code-block:: bash

  $ avocado run --job-timeout 50 /bin/true

Floats
~~~~~~

Float numbers has the same representation as integers, but you should use `.`
(dot) to separate the decimals. i.e: `80.3`.

Booleans
~~~~~~~~

When talking about configuration files, accepted values for a boolean option
are '1', 'yes', 'true', and 'on', which cause this method to return True, and
'0', 'no', 'false', and 'off', which cause it to return False. But, when
talking about command-line, booleans options don't need any argument, the
option itself will enable or disable the settings, depending on the context.

Example using the configuration file:

.. code-block:: ini

  [core]
  verbose = true

Example using the command-line:

.. code-block:: bash

  $ avocado run --verbose /bin/true

.. note:: Currently we still have some "old style boolean" options where you
  should pass "on" or "off" on the command-line. i.e: ``--json-job-result=off``.
  Those options are going to be replaced soon.

Lists
~~~~~

Lists are peculiar when configuring. On configuration files you can use the
default "python" syntax for lists: ``["foo", "bar"]``, but when using the
command-line arguments lists are strings separated by spaces:

Example using the configuration file:

.. code-block:: ini

  [assets.fetch]
  references = ["foo.py", "bar.py"]

Example using the command-line:

.. code-block:: bash

  $ avocado assets fetch foo.py bar.py


Complete Configuration Reference
--------------------------------

For a complete configuration reference, please visit :ref:`config-reference`.

.. _INI: http://en.wikipedia.org/wiki/INI_file

Or you can see in your terminal, typing::

    $ avocado config reference
