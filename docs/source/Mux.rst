.. _mux:

===================
Test variants - Mux
===================

The ``Mux`` is a special mechanism to produce multiple variants of the same
test with different parameters. This is essential in order to get a decent
coverage and avocado allows several ways to define those parameters from
simple enumeration of key/value pairs to complex trees which allows in simple
manner define test matrices with all possible variants.

This sounds similar to sparse matrix jobs in Jenkins, but the difference is
that instead of filters, which are available too, avocado allows specifying
so called ``mux domains``, which is a nicer way to represent data.
As the data is represented in trees it creates all possible variants
per domain and then all combinations of these. It sounds complicated, but
in reality it follows the way people are used to define dependencies,
therefor it's very simple to use and clear even in complex cases.

The best explanation comes usually from examples, so feel free to scroll down
to `yaml_to_mux plugin`_ section, which uses the default mux plugin to feed
the Mux.


Mux internals
-------------

The ``Mux`` is a core part of avocado and one can see it as a ``multiplexed``
database, which contains key/value pairs associated to given paths and
as we are talking about a tree of those, we call the paths ``Nodes``.

Mux allows iterating through all possible combinations which are stored in
the database, which is called ``multiplexation``. Mux yields ``variants``,
which are lists of leaf nodes with their values, which are then processed
into ``AvocadoParams``. Those params are available in tests as
``self.params`` and one can query for the current parameters::

    self.params.get(key="my_key", path="/some/location/*",
                    default="default_value")

Let's get back to Mux for a while. As mentioned earlier, it's a database
which allows storing multiple variants of test parameters. To fill the
database, you can use several commands.

1. ``--mux-inject`` - injects directly [path:]key:node values from the
   cmdline (see ``avocado multiplex -h``)
2. ``yaml_to_mux plugin`` - allows parsing ``yaml`` files into the Mux
   database (see `yaml_to_mux plugin`_)
3. Custom plugin using the simple ``Mux`` API (see `mux_api`_)


.. _mux_api:

Mux API
-------

.. warning:: This API is internal, we might change it at any moment. On the
             other hand we maintain ``avocado-virt`` plugin which uses this
             API so in such case we'd provide a patch there demonstrating
             the necessary changes.

The ``Mux`` object is defined in ``avocado/core/multiplexer.py``, is always
instantiated in ``avocado.core.parser.py`` and always available in
``args.mux``. The basic workflow is:

1. Initialize ``Mux`` in ``args.mux``
2. Fill it with data (``plugins`` or ``job``)
3. Multiplex it (in ``job``)
4. Iterate through all variants on all job's tests

Once the ``Mux`` object is multiplexed (3), it's restricted to alter the
data (2) to avoid changing the already produced data.

The main API needed for your plugins, which we are going to try keeping as
stable as possible is:

* mux.is_parsed() - to find out whether the object was already parsed
* data_inject(key, value, path=None) - to inject key/value pairs optionaly
  to a given path (by default '/')
* data_merge(tree) - to merge ``avocado.core.tree.TreeNode``-like tree
  into the database.

Given these you should be able to implement any kind of parser or params
feeder, should you require one. We favor ``yaml`` and therefor we implemented
a ``yaml_to_mux`` plugin which can be found in
``avocado/plugins/yaml_to_mux.py`` and on it we also describe the way
``Mux`` works: `yaml_to_mux plugin`_


Yaml_to_mux plugin
==================

In order to get a good coverage one always needs to execute the same test
with different parameters or in various environments. Avocado uses the
term ``Multiplexation`` or ``Mux`` to generate multiple variants of the same
test with different values. To define these variants and values
`YAML <http://www.yaml.org/>`_ files are used. The benefit of using YAML
file is the visible separation of different scopes. Even very advanced setups
are still human readable, unlike traditional sparse, multi-dimensional-matrices
of parameters.

Let's start with an example (line numbers at the first columns are for
documentation purposes only, they are not part of the multiplex file
format)::

     1  hw:
     2      cpu: !mux
     3          intel:
     4              cpu_CFLAGS: '-march=core2'
     5          amd:
     6              cpu_CFLAGS: '-march=athlon64'
     7          arm:
     8              cpu_CFLAGS: '-mabi=apcs-gnu -march=armv8-a -mtune=arm8'
     9      disk: !mux
    10          scsi:
    11              disk_type: 'scsi'
    12          virtio:
    13              disk_type: 'virtio'
    14  distro: !mux
    15      fedora:
    16          init: 'systemd'
    17      mint:
    18          init: 'systemv'
    19  env: !mux
    20      debug:
    21          opt_CFLAGS: '-O0 -g'
    22      prod:
    23          opt_CFLAGS: '-O2'


There are couple of key=>value pairs (lines 4,6,8,11,13,...) and there are
named nodes which define scope (lines 1,2,3,5,7,9,...). There are also additional
flags (lines 2, 9, 14, 19) which modifies the behavior.


Nodes
-----

They define context of the key=>value pairs allowing us to easily identify
for what this values might be used for and also it makes possible to define
multiple values of the same keys with different scope.

Due to their purpose the YAML automatic type conversion for nodes names
is disabled, so the value of node name is always as written in the yaml
file (unlike values, where `yes` converts to `True` and such).

Nodes are organized in parent-child relationship and together they create
a tree. To view this structure use ``avocado multiplex --tree -m <file>``::

 ┗━━ run
      ┣━━ hw
      ┃    ┣━━ cpu
      ┃    ┃    ╠══ intel
      ┃    ┃    ╠══ amd
      ┃    ┃    ╚══ arm
      ┃    ┗━━ disk
      ┃         ╠══ scsi
      ┃         ╚══ virtio
      ┣━━ distro
      ┃    ╠══ fedora
      ┃    ╚══ mint
      ┗━━ env
           ╠══ debug
           ╚══ prod

You can see that ``hw`` has 2 children ``cpu`` and ``disk``. All parameters
defined in parent node are inherited to children and extended/overwritten by
their values up to the leaf nodes. The leaf nodes (``intel``, ``amd``, ``arm``,
``scsi``, ...) are the most important as after multiplexation they form the
parameters available in tests.


Keys and Values
---------------

Every value other than dict (4,6,8,11) is used as value of the antecedent
node.

Each node can define key/value pairs (lines 4,6,8,11,...). Additionally
each children node inherits values of it's parent and the result is called
node ``environment``.

Given the node structure bellow::

    devtools:
        compiler: 'cc'
        flags:
            - '-O2'
        debug: '-g'
        fedora:
            compiler: 'gcc'
            flags:
                - '-Wall'
        osx:
            compiler: 'clang'
            flags:
                - '-arch i386'
                - '-arch x86_64'

And the rules defined as:

* Scalar values (Booleans, Numbers and Strings) are overwritten by walking from the root until the final node.
* Lists are appended (to the tail) whenever we walk from the root to the final node.

The environment created for the nodes ``fedora`` and ``osx`` are:

- Node ``//devtools/fedora`` environment ``compiler: 'gcc'``, ``flags: ['-O2', '-Wall']``
- Node ``//devtools/osx`` environment ``compiler: 'clang'``, ``flags: ['-O2', '-arch i386', '-arch x86_64']``

Note that due to different usage of key and values in environment we disabled
the automatic value conversion for keys while keeping it enabled for values.
This means that the value can be of any YAML supported value, eg. bool, None,
list or custom type, while the key is always string.

Variants
--------

In the end all leaves are gathered and turned into parameters, more specifically into
``AvocadoParams``::

    setup:
        graphic:
            user: "guest"
            password: "pass"
        text:
            user: "root"
            password: "123456"

produces ``[graphic, text]``. In the test code you'll be able to query only
those leaves. Intermediary or root nodes are available.

The example above generates a single test execution with parameters separated
by path. But the most powerful multiplexer feature is that it can generate
multiple variants. To do that you need to tag a node whose children are
ment to be multiplexed. Effectively it returns only leaves of one child at the
time.In order to generate all possible variants multiplexer creates cartesian
product of all of these variants::

    cpu: !mux
        intel:
        amd:
        arm:
    fmt: !mux
        qcow2:
        raw:

Produces 6 variants::

    /cpu/intel, /fmt/qcow2
    /cpu/intel, /fmt/raw
    ...
    /cpu/arm, /fmt/raw

The !mux evaluation is recursive so one variant can expand to multiple
ones::

    fmt: !mux
        qcow: !mux
            2:
            2v3:
        raw:

Results in::

    /fmt/qcow2/2
    /fmt/qcow2/2v3
    /raw


Resolution order
----------------

You can see that only leaves are part of the test parameters. It might happen
that some of these leaves contain different values of the same key. Then
you need to make sure your queries separate them by different paths. When
the path matches multiple results with different origin, an exception is raised
as it's impossible to guess which key was originally intended.

To avoid these problems it's recommended to use unique names in test parameters if
possible, to avoid the mentioned clashes. It also makes it easier to extend or mix
multiple YAML files for a test.

For multiplex YAML files that are part of a framework, contain default
configurations, or serve as plugin configurations and other advanced setups it is
possible and commonly desirable to use non-unique names. But always keep those points
in mind and provide sensible paths.

Multiplexer also supports default paths. By default it's ``/run/*`` but it can
be overridden by ``--mux-path``, which accepts multiple arguments. What it does
it splits leaves by the provided paths. Each query goes one by one through
those sub-trees and first one to hit the match returns the result. It might not
solve all problems, but it can help to combine existing YAML files with your
ones::

    qa:         # large and complex read-only file, content injected into /qa
        tests:
            timeout: 10
        ...
    my_variants: !mux        # your YAML file injected into /my_variants
        short:
            timeout: 1
        long:
            timeout: 1000

You want to use an existing test which uses ``params.get('timeout', '*')``.  Then you
can use ``--mux-path '/my_variants/*' '/qa/*'`` and it'll first look in your
variants. If no matches are found, then it would proceed to ``/qa/*``

Keep in mind that only slices defined in mux-path are taken into account for
relative paths (the ones starting with ``*``)


Injecting files
---------------

You can run any test with any YAML file by::

    avocado run sleeptest.py --mux-yaml file.yaml

This puts the content of ``file.yaml`` into ``/run``
location, which as mentioned in previous section, is the default ``mux-path``
path. For most simple cases this is the expected behavior as your files
are available in the default path and you can safely use ``params.get(key)``.

When you need to put a file into a different location, for example
when you have two files and you don't want the content to be merged into
a single place becomming effectively a single blob, you can do that by
giving a name to your yaml file::

    avocado run sleeptest.py --mux-yaml duration:duration.yaml

The content of ``duration.yaml`` is injected into ``/run/duration``. Still when
keys from other files don't clash, you can use ``params.get(key)`` and retrieve
from this location as it's in the default path, only extended by the
``duration`` intermediary node. Another benefit is you can merge or separate
multiple files by using the same or different name, or even a complex
(relative) path.

Last but not least, advanced users can inject the file into whatever location
they prefer by::

    avocado run sleeptest.py --mux-yaml /my/variants/duration:duration.yaml

Simple ``params.get(key)`` won't look in this location, which might be the
intention of the test writer. There are several ways to access the values:

* absolute location ``params.get(key, '/my/variants/duration')``
* absolute location with wildcards ``params.get(key, '/my/*)``
  (or ``/*/duration/*``...)
* set the mux-path ``avocado run ... --mux-path /my/*`` and use relative path

It's recommended to use the simple injection for single YAML files, relative
injection for multiple simple YAML files and the last option is for very
advanced setups when you either can't modify the YAML files and you need to
specify custom resoltion order or you are specifying non-test parameters, for
example parameters for your plugin, which you need to separate from the test
parameters.


Multiple files
--------------

You can provide multiple files. In such scenario final tree is a combination
of the provided files where later nodes with the same name override values of
the preceding corresponding node. New nodes are appended as new children::

    file-1.yaml:
        debug:
            CFLAGS: '-O0 -g'
        prod:
            CFLAGS: '-O2'

    file-2.yaml:
        prod:
            CFLAGS: '-Os'
        fast:
            CFLAGS: '-Ofast'

results in::

    debug:
        CFLAGS: '-O0 -g'
    prod:
        CFLAGS: '-Os'       # overriden
    fast:
        CFLAGS: '-Ofast'    # appended

It's also possible to include existing file into another a given node in another
file. This is done by the `!include : $path` directive::

    os:
        fedora:
            !include : fedora.yaml
        gentoo:
            !include : gentoo.yaml

.. warning:: Due to YAML nature, it's **mandatory** to put space between
             `!include` and the colon (`:`) that must follow it.

The file location can be either absolute path or relative path to the YAML
file where the `!include` is called (even when it's nested).

Whole file is **merged** into the node where it's defined.


Advanced YAML tags
------------------

There are additional features related to YAML files. Most of them require values
separated by ``":"``. Again, in all such cases it's mandatory to add a white space
(``" "``) between the tag and the ``":"``, otherwise ``":"`` is part of the tag
name and the parsing fails.

!include
--------

Includes other file and injects it into the node it's specified in::

    my_other_file:
        !include : other.yaml

The content of ``/my_other_file`` would be parsed from the ``other.yaml``. It's
the hardcoded equivalent of the ``-m $using:$path``.

Relative paths start from the original file's directory.

!using
------

Prepends path to the node it's defined in::

    !using : /foo
    bar:
        !using : baz

``bar`` is put into ``baz`` becoming ``/baz/bar`` and everything is put into
``/foo``. So the final path of ``bar`` is ``/foo/baz/bar``.

!remove_node
------------

Removes node if it existed during the merge. It can be used to extend
incompatible YAML files::

    os:
        fedora:
        windows:
            3.11:
            95:
    os:
        !remove_node : windows
        windows:
            win3.11:
            win95:

Removes the `windows` node from structure. It's different from `filter-out`
as it really removes the node (and all children) from the tree and
it can be replaced by you new structure as shown in the example. It removes
`windows` with all children and then replaces this structure with slightly
modified version.

As `!remove_node` is processed during merge, when you reverse the order,
windows is not removed and you end-up with `/windows/{win3.11,win95,3.11,95}`
nodes.

!remove_value
-------------

It's similar to `!remove_node`_ only with values.

!mux
----

Children of this node will be multiplexed. This means that in first variant
it'll return leaves of the first child, in second the leaves of the second
child, etc. Example is in section `Variants`_


Complete example
----------------

Let's take a second look at the first example::

     1    hw:
     2        cpu: !mux
     3            intel:
     4                cpu_CFLAGS: '-march=core2'
     5            amd:
     6                cpu_CFLAGS: '-march=athlon64'
     7            arm:
     8                cpu_CFLAGS: '-mabi=apcs-gnu -march=armv8-a -mtune=arm8'
     9        disk: !mux
    10            scsi:
    11                disk_type: 'scsi'
    12            virtio:
    13                disk_type: 'virtio'
    14    distro: !mux
    15        fedora:
    16            init: 'systemd'
    17        mint:
    18            init: 'systemv'
    19    env: !mux
    20        debug:
    21            opt_CFLAGS: '-O0 -g'
    22        prod:
    23            opt_CFLAGS: '-O2'

After filters are applied (simply removes non-matching variants), leaves
are gathered and all variants are generated::

    $ avocado multiplex -m examples/mux-environment.yaml
    Variants generated:
    Variant 1:    /hw/cpu/intel, /hw/disk/scsi, /distro/fedora, /env/debug
    Variant 2:    /hw/cpu/intel, /hw/disk/scsi, /distro/fedora, /env/prod
    Variant 3:    /hw/cpu/intel, /hw/disk/scsi, /distro/mint, /env/debug
    Variant 4:    /hw/cpu/intel, /hw/disk/scsi, /distro/mint, /env/prod
    Variant 5:    /hw/cpu/intel, /hw/disk/virtio, /distro/fedora, /env/debug
    Variant 6:    /hw/cpu/intel, /hw/disk/virtio, /distro/fedora, /env/prod
    Variant 7:    /hw/cpu/intel, /hw/disk/virtio, /distro/mint, /env/debug
    Variant 8:    /hw/cpu/intel, /hw/disk/virtio, /distro/mint, /env/prod
    Variant 9:    /hw/cpu/amd, /hw/disk/scsi, /distro/fedora, /env/debug
    Variant 10:    /hw/cpu/amd, /hw/disk/scsi, /distro/fedora, /env/prod
    Variant 11:    /hw/cpu/amd, /hw/disk/scsi, /distro/mint, /env/debug
    Variant 12:    /hw/cpu/amd, /hw/disk/scsi, /distro/mint, /env/prod
    Variant 13:    /hw/cpu/amd, /hw/disk/virtio, /distro/fedora, /env/debug
    Variant 14:    /hw/cpu/amd, /hw/disk/virtio, /distro/fedora, /env/prod
    Variant 15:    /hw/cpu/amd, /hw/disk/virtio, /distro/mint, /env/debug
    Variant 16:    /hw/cpu/amd, /hw/disk/virtio, /distro/mint, /env/prod
    Variant 17:    /hw/cpu/arm, /hw/disk/scsi, /distro/fedora, /env/debug
    Variant 18:    /hw/cpu/arm, /hw/disk/scsi, /distro/fedora, /env/prod
    Variant 19:    /hw/cpu/arm, /hw/disk/scsi, /distro/mint, /env/debug
    Variant 20:    /hw/cpu/arm, /hw/disk/scsi, /distro/mint, /env/prod
    Variant 21:    /hw/cpu/arm, /hw/disk/virtio, /distro/fedora, /env/debug
    Variant 22:    /hw/cpu/arm, /hw/disk/virtio, /distro/fedora, /env/prod
    Variant 23:    /hw/cpu/arm, /hw/disk/virtio, /distro/mint, /env/debug
    Variant 24:    /hw/cpu/arm, /hw/disk/virtio, /distro/mint, /env/prod

Where the first variant contains::

    /hw/cpu/intel/  => cpu_CFLAGS: -march=core2
    /hw/disk/       => disk_type: scsi
    /distro/fedora/ => init: systemd
    /env/debug/     => opt_CFLAGS: -O0 -g

The second one::

    /hw/cpu/intel/  => cpu_CFLAGS: -march=core2
    /hw/disk/       => disk_type: scsi
    /distro/fedora/ => init: systemd
    /env/prod/      => opt_CFLAGS: -O2

From this example you can see that querying for ``/env/debug`` works only in
the first variant, but returns nothing in the second variant. Keep this in mind
and when you use the ``!mux`` flag always query for the pre-mux path,
``/env/*`` in this example.
