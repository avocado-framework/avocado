=====================
Avocado Configuration
=====================

Avocado utilities have a certain default behavior based on educated, reasonable (we hope) guesses about how
users like to use their systems. Of course, different people will have different needs and/or dislike our defaults,
and that's why a configuration system is in place to help with those cases

The avocado config file format is based on the (informal)
`INI file 'specification' <http://en.wikipedia.org/wiki/INI_file>`__, that is implemented by
python's  :mod:`ConfigParser`. The format is simple and straightforward, composed by `sections`,
that contain a number of `keys` and `values`. Take for example a basic avocado config file::

    [runner]
    base_dir = ~/avocado
    test_dir = /home/lmr/Code/avocado.lmr/examples/tests
    data_dir = /usr/share/avocado/data
    logs_dir = ~/avocado/job-results
    tmp_dir = /var/tmp/avocado

The ``runner`` section contains a number of keys, all of them related to directories used by
the test runner. The ``base_dir`` is the base directory to other important avocado directories, such
as log, data and test directories. You can also choose to set those other important directories by
means of the variables ``test_dir``, ``data_dir``, ``logs_dir`` and ``tmp_dir``. You can do this by
simply editing the config files available.


Config file parsing order
=========================

Avocado starts by parsing what it calls system wide config file, that is shipped to all avocado users on a system
wide directory, ``/etc/avocado/avocado.conf``. Then it'll verify if there's a local user config file, that is located
usually in ``~/.config/avocado/avocado.conf``. The order of the parsing matters, so the system wide file is parsed,
then the user config file is parsed last, so that the user can override values at will.

Please note that for base directories, if you chose a directory that can't be properly used by avocado (some directories
require read access, others, read and write access), avocado will fall back to some defaults. So if your regular user
wants to write logs to ``/root/avocado/logs``, avocado will not use that directory, since it can't write files to that
place. A new location, by default ``~/avocado/job-results`` will be selected instead.

Plugin config files
===================

Plugins can also be configured by config files. In order to not disturb the main avocado config file, those plugins,
if they wish so, may install additional config files to ``/etc/avocado/conf.d/[pluginname].conf``, that will be parsed
after the system wide config file. Users can override those values as well at the local config file level. So considering
the hypothetical plugin config::

    [plugin.salad]
    base = ceasar
    dressing = ceasar

If you want, you may change ``dressing`` in your config file by simply adding a ``[plugin.salad]`` new section in your
local config file, and set a different value for ``dressing`` there.

Parsing order recap
===================

So the parsing order is:

* ``/etc/avocado/avocado.conf``
* ``/etc/avocado/conf.d/*.conf``
* ``~/.config/avocado/avocado.conf``

In this order, meaning that what you set on your local config file may override what's defined in the system wide files.

Config plugin
=============

A configuration plugin is provided for users that wish to quickly see what's defined in all sections of their avocado
configuration, after all the files are parsed in their correct resolution order. Example::

    $ avocado config
    Config files read (in order):
        /etc/avocado/avocado.conf
        /home/lmr/.config/avocado/avocado.conf

        Section.Key     Value
        runner.base_dir /usr/share/avocado
        runner.test_dir /home/lmr/Code/avocado.lmr/examples/tests
        runner.data_dir /usr/share/avocado/data
        runner.logs_dir ~/avocado/job-results
        runner.tmp_dir  /var/tmp/avocado

The command also shows the order in which your config files were parsed, giving you a better understanding of
what's going on. The Section.Key nomenclature was inspired in ``git config --list`` output.
