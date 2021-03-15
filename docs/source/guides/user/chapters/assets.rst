.. _managing-assets:

Managing Assets
===============

..note:: Please note that we are improve constantly how we handle assets inside
         Avocado. Probably some changes will be delivered during the next
         releases.

Assets are artifacts that can be used in your tests. Avocado can download those
assets automatically when parsing your tests or on demand, when you register an
asset at the command-line.

Sometimes those assets, depending on your case, can be a bottleneck when it
comes to disk space. If you are constantly using large assets in your tests, it
is important to have a good idea on how Avocado stores and handle those
artifacts.

TODO: [Improve this section describing assets in general]

Listing assets
--------------

If you would like to list assets that are cached in your system, you can run
the following command::

 $ avocado assets list

This command supports `--by-size-filter` and `--by-days` options. When using
the former you should pass a comparison filter and a size in bytes. For
instance::

 $ avocado assets list --by-size-filter=">=2048"

The command above will list only assets bigger than 2Kb. We support the
following operators: `=`, `>=`, `<=`, `<` and `>`.

Now, if you are looking for assets older (based on the acces time) than 10
days, you could use this command::

 $ avocado assets list --by-days=10

Removing assets
---------------

You can remove the files in your cache directories manually. However, we have
provided a utility to help you with that::

 $ avocado assets purge --help

Assets can be removed applying the same filters as described when listing them.
You can remove assets by a size filter (`--by-size-filter`) or assets older
than N days (`--by-days`).

Changing the default cache dirs
-------------------------------

Assets are stored inside the `datadir.paths.cache_dirs` option. You can change
this in your configuration file and discover your current value with the
following command::

 $ avocado config | grep datadir.paths.cache_dirs
