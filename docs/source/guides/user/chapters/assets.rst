.. _managing-assets:

Managing Assets
===============

.. note:: Please note that we are constantly improving on how we handle assets
   inside Avocado. Probably some changes will be delivered during the next
   releases.

Assets are test artifacts that Avocado can download automatically either
during the test execution, or before the test even starts (by parsing the
test code or on-demand, manually registering them at the command-line).

Sometimes, depending on the use case, those assets can be a bottleneck for
disk space. If the tests constantly use large assets, it is important to know
how Avocado stores and handles those artifacts.

Listing assets
--------------

To list cached assets in the system, use the following command::

 $ avocado assets list

This command supports ``--by-size-filter`` and ``--by-days`` options. When
using the former, use a comparison filter and a size in bytes. For instance::

 $ avocado assets list --by-size-filter=">=2048"

The command above will list only assets bigger than 2Kb. Avocado supports the
following operators: `=`, `>=`, `<=`, `<` and `>`.

Now, to look for old assets (based on the access time), for example, 10 days
older, use the ``--by-days`` option::

 $ avocado assets list --by-days=10

Removing assets
---------------

It is possible to remove files from the cache directories manually. The
``purge`` utility helps with that:

 $ avocado assets purge --help

Assets can be removed applying the same filters as described when listing them.
It is possible to remove assets by a size filter (``--by-size-filter``) or
assets older than N days (``--by-days``).

.. _assets-removing-by-overall-cache-limit:

Removing by overall cache limit
-------------------------------

Besides the existing features, Avocado is able to set an overall limit, so that
it matches the storage limitations locally or on CI systems.

For instance it may be the case that a GitLab cache limit is 4 GiB, in that
case Avocado can sort assets  by last access, and remove all that exceeds
4 GiB (that is, keep the last accessed 4 GiB worth of cached files). Use the
``--by-overall-limit`` option specifying the size limit::

 $ avocado assets purge --by-overall-limit=4g

This ensures that the files which are not used for some time in the cache are
automatically removed.

Please, note that at the moment, you can only use 'b', 'k', 'm', 'g', and 't'as
suffixes.

Changing the default cache dirs
-------------------------------

Assets are stored inside the ``datadir.paths.cache_dirs`` option. It is possible
to change this in the configuration file. The current value is shown with the
following command::

 $ avocado config | grep datadir.paths.cache_dirs
