.. _managing-assets:

Managing Assets
===============

.. note:: Please note that we are constantly improving on how we handle assets
   inside Avocado. Probably some changes will be delivered during the next
   releases.

Assets are test artifacts that Avocado can download automatically either
during the test execution, or before the test even starts (by parsing the
test code or on-demand, manually registering them at the command-line).

Sometimes those assets, depending on your case, can be a bottleneck when it
comes to disk space. If you are constantly using large assets in your tests,
it is important to have a good idea of how Avocado stores and handles those
artifacts.

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

.. _assets-removing-by-overall-cache-limit:

Removing by overall cache limit
-------------------------------

Besides the existing features, Avocado is able to set an overall limit, so that
it matches the storage limitations of users (and CI systems).

For instance it may be the case that a GitLab cache limit is 4 GiB, in that
case we can sort by last access, and remove all that exceeds 4 GiB (that is,
keep the last accessed 4 GiB worth of cached files). You can run the following
command::

 $ avocado assets purge --by-overall-limit=4g

This would ensure that the cache is automatically being removed of files that
were used last (and possibly not used anymore).

Please, note that at the moment, you can only use 'b', 'k', 'm', 'g' and 't' as
suffix.

Changing the default cache dirs
-------------------------------

Assets are stored inside the `datadir.paths.cache_dirs` option. You can change
this in your configuration file and discover your current value with the
following command::

 $ avocado config | grep datadir.paths.cache_dirs
