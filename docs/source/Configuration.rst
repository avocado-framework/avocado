===============
 Configuration
===============

Avocado utilities have a certain default behavior based on educated, reasonable (we hope) guesses about how
users like to use their systems. Of course, different people will have different needs and/or dislike our defaults,
and that's why a configuration system is in place to help with those cases

The Avocado config file format is based on the (informal)
`INI file 'specification' <http://en.wikipedia.org/wiki/INI_file>`__, that is implemented by
Python's  :mod:`ConfigParser`. The format is simple and straightforward, composed by `sections`,
that contain a number of `keys` and `values`. Take for example a basic Avocado config file:

.. code-block:: ini

    [datadir.paths]
    base_dir = /var/lib/avocado
    test_dir = /usr/share/doc/avocado/tests
    data_dir = /var/lib/avocado/data
    logs_dir = ~/avocado/job-results

The ``datadir.paths`` section contains a number of keys, all of them related to directories used by
the test runner. The ``base_dir`` is the base directory to other important Avocado directories, such
as log, data and test directories. You can also choose to set those other important directories by
means of the variables ``test_dir``, ``data_dir`` and ``logs_dir``. You can do this by simply editing
the config files available.


Config file parsing order
=========================

Avocado starts by parsing what it calls system wide config file, that is shipped to all Avocado users on a system
wide directory, ``/etc/avocado/avocado.conf``. Then it'll verify if there's a local user config file, that is located
usually in ``~/.config/avocado/avocado.conf``. The order of the parsing matters, so the system wide file is parsed,
then the user config file is parsed last, so that the user can override values at will. There is another directory
that will be scanned by extra config files, ``/etc/avocado/conf.d``. This directory may contain plugin config files,
and extra additional config files that the system administrator/avocado developers might judge necessary to put there.

Please note that for base directories, if you chose a directory that can't be properly used by Avocado (some directories
require read access, others, read and write access), Avocado will fall back to some defaults. So if your regular user
wants to write logs to ``/root/avocado/logs``, Avocado will not use that directory, since it can't write files to that
place. A new location, by default ``~/avocado/job-results`` will be selected instead.

The order of files described in this section is only valid if avocado was installed in the system. For people using
avocado from git repos (usually avocado developers), that did not install it in the system, keep in mind that avocado
will read the config files present in the git repos, and will ignore the system wide config files. Running
``avocado config`` will let you know which files are actually being used.

Plugin config files
===================

There are two ways to extend settings of extra plugin configuration. Plugins
can extend the list of files parsed by ``Settings`` object by using
``avocado.plugins.settings`` entry-point (Python-way) or they can
simply drop the individual config files into ``/etc/avocado/conf.d``
(linux/posix-way).

`avocado.plugins.settings`
--------------------------

This entry-point uses ``avocado.core.plugin_interfaces.Settings``-like object
to extend the list of parsed files. It only accepts individual files, but
you can use something like ``glob.glob("*.conf")`` to add all config files
inside a directory.

You need to create the plugin (eg. ``my_plugin/settings.py``)::

   from avocado.core.plugin_interfaces import Settings

   class MyPluginSettings(Settings):
       def adjust_settings_paths(self, paths):
           paths.extend(glob.glob("/etc/my_plugin/conf.d/*.conf"))


And register it in your ``setup.py`` entry-points::

   from setuptools import setup
   ...
   setup(name="my-plugin",
         entry_points={
             'avocado.plugins.settings': [
                 "my-plugin-settings = my_plugin.settings.MyPluginSettings",
                 ],
             ...

Which extends the list of files to be parsed by settings object. Note this
has to be executed early in the code so try to keep the required deps
minimal (for example the `avocado.core.settings.settings` is not yet
available).

`/etc/avocado/conf.d`
---------------------

In order to not disturb the main Avocado config file, those plugins,
if they wish so, may install additional config files to
``/etc/avocado/conf.d/[pluginname].conf``, that will be parsed
after the system wide config file. Users can override those values
as well at the local config file level. Considering the config for
the hypothethical plugin ``salad``:

.. code-block:: ini

    [salad.core]
    base = ceasar
    dressing = ceasar

If you want, you may change ``dressing`` in your config file by simply adding a ``[salad.core]`` new section in your
local config file, and set a different value for ``dressing`` there.

Parsing order recap
===================

So the file parsing order is:

* ``/etc/avocado/avocado.conf``
* ``/etc/avocado/conf.d/*.conf``
* ``avocado.plugins.settings`` plugins (but they can insert to any location)
* ``~/.config/avocado/avocado.conf``

You can see the actual set of files/location by using ``avocado config``
which uses ``*`` to mark existing and used files::

   $ avocado config
   Config files read (in order, '*' means the file exists and had been read):
    * /etc/avocado/avocado.conf
    * /etc/avocado/conf.d/resultsdb.conf
    * /etc/avocado/conf.d/result_upload.conf
    * /etc/avocado/conf.d/jobscripts.conf
    * /etc/avocado/conf.d/gdb.conf
    * /etc/avocado_vt/conf.d/vt.conf
    * /etc/avocado_vt/conf.d/vt_joblock.conf
      /home/medic/.config/avocado/avocado.conf

    Section.Key                              Value
    datadir.paths.base_dir                   /var/lib/avocado
    datadir.paths.test_dir                   /usr/share/doc/avocado/tests
    ...


Where the lower config files override values of the upper files and
the ``/home/medic/.config/avocado/avocado.conf`` file missing.

.. note::  Please note that if avocado is running from git repos, those files will be ignored in favor of in tree configuration files. This is something that would normally only affect people developing avocado, and if you are in doubt, ``avocado config`` will tell you exactly which files are being used in any given situation.
.. note::  When avocado runs inside virtualenv than path for global config files is also changed. For example, `avocado.conf` comes from the virual-env path `venv/etc/avocado/avocado.conf`.


Order of precedence for values used in tests
============================================

Since you can use the config system to alter behavior and values used in tests (think paths to test programs, for
example), we established the following order of precedence for variables (from least precedence to most):

* default value (from library or test code)
* global config file
* local (user) config file
* command line switch
* test parameters

So the least important value comes from the library or test code default,
going all the way up to the test parameters system.

Avocado Data Directories
========================

When running tests, we are frequently looking to:

* Locate tests
* Write logs to a given location
* Grab files that will be useful for tests, such as ISO files or VM disk
  images

Avocado has a module dedicated to find those paths, to avoid cumbersome
path manipulation magic that people had to do in previous test frameworks [#f1]_.

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
    file to customize values

    Avocado Data Directories:
        base  $HOME/avocado
        tests $HOME/Code/avocado/examples/tests
        data  $HOME/avocado/data
        logs  $HOME/avocado/job-results

Note that, while Avocado will do its best to use the config values you
provide in the config file, if it can't write values to the locations
provided, it will fall back to (we hope) reasonable defaults, and we
notify the user about that in the output of the command.

The relevant API documentation and meaning of each of those data directories
is in :mod:`avocado.core.data_dir`, so it's highly recommended you take a look.

You may set your preferred data dirs by setting them in the Avocado config files.
The only exception for important data dirs here is the Avocado tmp dir, used to
place temporary files used by tests. That directory will be in normal circumstances
`/var/tmp/avocado_XXXXX`, (where `XXXXX` is in actuality a random string) securely
created on `/var/tmp/`, unless the user has the `$TMPDIR` environment variable set,
since that is customary among unix programs.

The next section of the documentation explains how you can see and set config
values that modify the behavior for the Avocado utilities and plugins.

.. [#f1] For example, autotest.
