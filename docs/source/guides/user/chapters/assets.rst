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

Registering assets
------------------

To manually register a local asset in the cache, use the ``register`` command::

 $ avocado assets register *NAME* *URL*

Where ``NAME`` is the unique name to associate with this asset and ``URL`` is
the path to the local asset to be manually registered.

The ``register`` command also supports the ``--hash`` option, which allows the
addition of the file's hash.

Fetching assets from instrumented tests
---------------------------------------

The ``fetch`` command allows the download of a limited definition of  assets
inside an Avocado Instrumented test. It uses a parser on instrumented test
source to find ``fetch_asset`` calls composed of simple strings as parameters,
or at least one level of variable in the same context with a string assignment,
and fetch those assets without running the test. The only exception to strings
as arguments is the ``locations`` parameter, which allows the user of a list.

Following are some examples of supported definitions of assets by the ``fetch``
command:

.. code-block:: python

    tarball_locations = [
        'https://mirrors.peers.community/mirrors/gnu/hello/hello-2.9.tar.gz',
        'https://mirrors.kernel.org/gnu/hello/hello-2.9.tar.gz',
        'http://gnu.c3sl.ufpr.br/ftp/hello-2.9.tar.gz',
        'ftp://ftp.funet.fi/pub/gnu/prep/hello/hello-2.9.tar.gz'
        ]
    self.hello = self.fetch_asset(
        name='hello-2.9.tar.gz',
        asset_hash='cb0470b0e8f4f7768338f5c5cfe1688c90fbbc74',
        locations=tarball_locations)

.. code-block:: python

    kernel_url = ('https://archives.fedoraproject.org/pub/archive/fedora'
                  '/linux/releases/29/Everything/x86_64/os/images/pxeboot'
                  '/vmlinuz')
    kernel_hash = '23bebd2680757891cf7adedb033532163a792495'
    kernel_path = self.fetch_asset(kernel_url, asset_hash=kernel_hash)

To fetch the assets defined inside an instrumented test, use::

 $ avocado assets fetch *AVOCADO_INSTRUMENTED*

Where ``AVOCADO_INSTRUMENTED`` is the path to the Avocado Instrumented file.

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
