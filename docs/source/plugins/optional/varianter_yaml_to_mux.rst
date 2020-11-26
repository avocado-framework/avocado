.. _yaml-to-mux-plugin:

Yaml_to_mux plugin
==================

:mod:`avocado_varianter_yaml_to_mux`

This plugin utilizes the ``multiplexation`` mechanism to
produce variants out of a yaml file. This section is example-based,
if you are interested in test parameters and/or ``multiplexation``
overview, please take a look at :ref:`test-parameters`.

As mentioned earlier, it inherits from the
:class:`avocado_varianter_yaml_to_mux.mux.MuxPlugin`
and the only thing it implements is the argument parsing
to get some input and a custom ``yaml``
parser (which is also capable of parsing ``json``).

The YAML file is perfect for this task as it's easily read by
both, humans and machines.  Let's start with an example (line
numbers at the first columns are for documentation purposes only,
they are not part of the multiplex file format):

.. code-block:: yaml

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


.. warning:: On some architectures misbehaving versions of CYaml
   Python library were reported and Avocado always fails with
   ``unacceptable character #x0000: control characters are not
   allowed``. To workaround this issue you need to either update
   the PyYaml to the version which works properly, or you need
   to remove the ``python2.7/site-packages/yaml/cyaml.py`` or
   disable CYaml import in Avocado sources. For details check
   out the `Github issue <https://github.com/avocado-framework/avocado/issues/1190>`_

There are couple of key=>value pairs (lines 4,6,8,11,13,...) and there are
named nodes which define scope (lines 1,2,3,5,7,9,...). There are also additional
flags (lines 2, 9, 14, 19) which modifies the behavior.


Nodes
-----

They define context of the key=>value pairs allowing us to easily identify
for what this values might be used for and also it makes possible to define
multiple values of the same keys with different scope.

Due to their purpose the YAML automatic type conversion for nodes names
is disabled, so the value of node name is always as written in the YAML
file (unlike values, where `yes` converts to `True` and such).

Nodes are organized in parent-child relationship and together they create
a tree. To view this structure use ``avocado variants --tree -m <file>``::

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

Given the node structure bellow:

.. code-block:: yaml

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
This means that the key is always a string and the value can be YAML value,
eg. bool, list, custom type, or string. Please be aware that due to limitation
None type can be provided in yaml specifically as string 'null'.

Variants
--------

In the end all leaves are gathered and turned into parameters, more specifically into
``AvocadoParams``:

.. code-block:: yaml

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
product of all of these variants:

.. code-block:: yaml

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
ones:

.. code-block:: yaml

    fmt: !mux
        qcow: !mux
            2:
            2v3:
        raw:

Results in::

    /fmt/qcow2/2
    /fmt/qcow2/2v3
    /raw


.. _yaml-to-mux-resolution-order:

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
ones:

.. code-block:: yaml

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
a single place becoming effectively a single blob, you can do that by
giving a name to your YAML file::

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
specify custom resolution order or you are specifying non-test parameters, for
example parameters for your plugin, which you need to separate from the test
parameters.


Special values
--------------

As you might have noticed, we are using mapping/dicts to define the structure
of the params. To avoid surprises we disallowed the smart typing of mapping
keys so:

.. code-block:: yaml

   on: on

Won't become ``True: True``, but the key will be preserved as string
``on: True``.

You might also want to use dict as values in your params. This is also
supported but as we can't easily distinguish whether that value is
a value or a node (structure), you have to either embed it into another
object (list, ..) or you have to clearly state the type (yaml tag
``!!python/dict``). Even then the value won't be a standard dictionary,
but it'll be ``collections.OrderedDict`` and similarly to nodes
structure all keys are preserved as strings and no smart type detection
is used. Apart from that it should behave similarly as dict, only you
get the values ordered by the order they appear in the file.

Multiple files
--------------

You can provide multiple files. In such scenario final tree is a combination
of the provided files where later nodes with the same name override values of
the preceding corresponding node. New nodes are appended as new children:

.. code-block:: yaml

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

results in:

.. code-block:: yaml

    debug:
        CFLAGS: '-O0 -g'
    prod:
        CFLAGS: '-Os'       # overriden
    fast:
        CFLAGS: '-Ofast'    # appended

It's also possible to include existing file into another a given node in another
file. This is done by the `!include : $path` directive:

.. code-block:: yaml

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
^^^^^^^^

Includes other file and injects it into the node it's specified in:

.. code-block:: yaml

    my_other_file:
        !include : other.yaml

The content of ``/my_other_file`` would be parsed from the ``other.yaml``. It's
the hardcoded equivalent of the ``-m $using:$path``.

Relative paths start from the original file's directory.

!using
^^^^^^

Prepends path to the node it's defined in:

.. code-block:: yaml

    !using : /foo
    bar:
        !using : baz

``bar`` is put into ``baz`` becoming ``/baz/bar`` and everything is put into
``/foo``. So the final path of ``bar`` is ``/foo/baz/bar``.

!remove_node
^^^^^^^^^^^^

Removes node if it existed during the merge. It can be used to extend
incompatible YAML files:

.. code-block:: yaml

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
^^^^^^^^^^^^^

It's similar to `!remove_node`_ only with values.

!mux
^^^^

Children of this node will be multiplexed. This means that in first variant
it'll return leaves of the first child, in second the leaves of the second
child, etc. Example is in section `Variants`_

!filter-only
------------

Defines internal filters. They are inherited by children and evaluated
during multiplexation. It allows one to specify the only compatible branch
of the tree with the current variant, for example::

    cpu:
        arm:
            !filter-only : /disk/virtio
    disk:
        virtio:
        scsi:

will skip the ``[arm, scsi]`` variant and result only in ``[arm, virtio]``

_Note: It's possible to use ``!filter-only`` multiple times with the same
parent and all allowed variants will be included (unless they are
filtered-out by ``!filter-out``)_

_Note2: The evaluation order is 1. filter-out, 2. filter-only. This means when
you booth filter-out and filter-only a branch it won't take part in the
multiplexed variants._

!filter-out
-----------

Similarly to `!filter-only`_ only it skips the specified branches and leaves
the remaining ones. (in the same example the use of
``!filter-out : /disk/scsi`` results in the same behavior). The difference
is when a new disk type is introduced, ``!filter-only`` still allows just
the specified variants, while ``!filter-out`` only removes the specified
ones.

As for the speed optimization, currently Avocado is strongly optimized
towards fast ``!filter-out`` so it's highly recommended using them
rather than ``!filter-only``, which takes significantly longer to
process.

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

    $ avocado variants -m selftests/.data/mux-environment.yaml
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


Injecting values
----------------

Beyond the values injected by YAML files specified it's also possible
inject values directly from command line to the final multiplex tree.
It's done by the argument  ``--mux-inject``. The format of expected
value is ``[path:]key:node_value``.

.. warning:: When no path is specified to ``--mux-inject`` the parameter
   is added under tree root ``/``. For example: running avocado passing
   ``--mux-inject my_key:my_value`` the parameter can be accessed calling
   ``self.params.get('my_key')``. If the test writer wants to put the injected
   value in any other path location, like extending the ``/run`` path, it needs
   to be informed on avocado run call.  For example: ``--mux-inject
   /run/:my_key:my_value`` makes possible to access the parameters
   calling ``self.params.get('my_key', '/run')``


A test that gets parameters without a defined path, such as
``examples/tests/multiplextest.py``::

   os_type = self.params.get('os_type', default='linux')

Running it::

   $ avocado --show=test run -- examples/tests/multiplextest.py  | grep os_type
   PARAMS (key=os_type, path=*, default=linux) => 'linux'

Now, injecting a value, by default will put it in /, which is not in the
default list of paths searched for::

   $ avocado --show=test run --mux-inject os_type:myos -- examples/tests/multiplextest.py  | grep os_type
   PARAMS (key=os_type, path=*, default=linux) => 'linux'

A path that is searched for by default is /run. To set the value to that path use::

   $ avocado --show=test run --mux-inject /run:os_type:myos -- examples/tests/multiplextest.py  | grep os_type
   PARAMS (key=os_type, path=*, default=linux) => 'myos'

Or, add the / to the list of paths searched for by default::

   $ avocado --show=test run --mux-inject os_type:myos --mux-path / -- examples/tests/multiplextest.py  | grep os_type
   PARAMS (key=os_type, path=*, default=linux) => 'myos'

.. warning:: By default, the values are parsed for the respective data types.
   When not possible, it falls back to string. If you want to maintain some
   value as string, enclose within quotes, properly escaped, and eclose that
   again in quotes.
   For example: a value of ``1`` is treated as integer, a value of ``1,2`` is
   treated as list, a value of ``abc`` is treated as string, a value of
   ``1,2,5-10`` is treated as list of integers as ``1,2,-5``. If you want to
   maintain this as string, provide the value as ``"\"1,2,5-10\""``
