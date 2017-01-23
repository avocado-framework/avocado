===============
Test parameters
===============

.. note:: This section describes in detail what are test parameters and how
   the whole variants mechanism works in avocado. If you're interested in
   basics, see :ref:`accessing-test-parameters` or practical view by examples
   in `Yaml_to_mux plugin`_.

.. warning:: The multiplexer is under heavy refactor and some of the APIs
   might still change in the following months (written on 2016-01-22),
   then we'll do our best to keep the public interfaces as stable as
   possible.

Avocado allows passing parameters to each executed test or even running
several variants of each test. These parameters are available in (test's)
``self.params`` and are of :mod:`avocado.core.varianter.AvocadoParams` type.

The data for ``self.params`` are supplied by
:mod:`avocado.core.varianter.Varianter` which asks all registered plugins
for variants or uses default when no variants are defined.

Overall picture of how the params handling works is:

.. following figure is not really a C code, but it renders well and it
   increases the visibility.

.. code-block:: c

       +-----------+
       |           |  // Test uses variant to produce AvocadoParams
       |   Test    |
       |           |
       +-----^-----+
             |  // single variant is passed to Test
             |
       +-----------+
       |  Runner   |  // iterates through tests and runs each test with
       +-----^-----+  // all variants supplied by Varianter
             |
             |
   +-------------------+ provide variants +-----------------------+
   |                   |<-----------------|                       |
   | Varianter API     |                  | Varianter plugins API |
   |                   |----------------->|                       |
   +-------------------+  update defaults +-----------------------+
             ^                                ^
             |                                |
             |  // default params injected    |  // All plugins are invoked
   +--------------------------------------+   |  // in turns
   | +--------------+ +-----------------+ |   |
   | | avocado-virt | | other providers | |   |
   | +--------------+ +-----------------+ |   |
   +--------------------------------------+   |
                                              |
                 +----------------------------+-----+
                 |                                  |
                 |                                  |
                 v                                  v
       +--------------------+           +-------------------------+
       | yaml_to_mux plugin |           | Other variant plugin(s) |
       +-----^--------------+           +-------------------------+
             |
             |  // yaml is parsed to MuxTree,
             |  // multiplexed and yields variants
       +---------------------------------+
       | +------------+ +--------------+ |
       | | --mux-yaml | | --mux-inject | |
       | +------------+ +--------------+ |
       +---------------------------------+


Let's introduce the basic keywords.

Test's default params
~~~~~~~~~~~~~~~~~~~~~

:mod:`avocado.core.test.Test.default_params`

Every (instrumented) test can hardcode default params by storing a dict
in ``self.default_params``. This attribute is checked during test's
``__init__`` phase and if present (before the
:mod:`avocado.core.test.Test.__init__` is executed) it's used by
`AvocadoParams`_.

.. warning:: Don't confuse `Test's default params`_ with `Default params`

TreeNode
~~~~~~~~

:mod:`avocado.core.varianter.TreeNode`

Is a node object allowing to create tree-like structures with
parent->multiple_children relations and storing params. It can
also report it's environment, which is set of params gathered
from root to this node. This is used in tests where instead of
passing the full tree only the leaf nodes are passed and their
environment represents all the values of the tree.

AvocadoParams
~~~~~~~~~~~~~

:mod:`avocado.core.varianter.AvocadoParams`

Is a "database" of params present in every (instrumented) avocado test.
It's produced during ``Test.__init__`` from a `variant`_. It accepts
a list of `TreeNode`_ objects; test name
:mod:`avocado.core.test.TestName` (for logging purposes); list of
default paths (`Mux path`_) and the `Test's default params`_.

In test it allows querying for data by using::

   self.params.get($name, $path=None, $default=None)

Where:

* name - name of the parameter (key)
* path - where to look for this parameter (when not specified uses mux-path)
* default - what to return when param not found

Each `variant`_ defines a hierarchy, which is preserved so `AvocadoParams`_
follows it to return the most appropriate value or raise Exception on error.

Mux path
~~~~~~~~

As test params are organized in trees, it's possible to have the same
variant in several locations. When they are produced from the same
`TreeNode`_, it's not a problem, but when they are a different values
there is no way to distinguish which should be reported. One way is
to use specific paths, when asking for params, but sometimes, usually
when combining upstream and downstream variants, we want to get our
values first and fall-back to the upstream ones when they are not found.

For example let's say we have upstream values in ``/upstream/sleeptest``
and our values in ``/downstream/sleeptest``. If we asked for a value using
path ``"*"``, it'd raise an exception being unable to distinguish whether
we want the value from ``/downstream`` or ``/upstream``. We can set the
mux path to ``["/downstream/*", "/upstream/*"]`` to make all relative
calls (path starting with ``*``) to first look in nodes in ``/downstream``
and if not found look into ``/upstream``.

More practical overview of mux path is in `yaml_to_mux plugin`_ in
`Resolution order`_ section.

Variant
~~~~~~~

Variant is a set of params produced by `VarianterPlugin`_s and passed to
the test by the test runner as ``params`` argument. The simplest variant
is ``None``, which still produces `AvocadoParams`_ with only the
`Test's default params`_. If dict is used as a `Variant`_, it (safely)
updates the default params. Last but not least the `Variant`_ can also
be a ``tuple(list, mux_path)`` or just the ``list`` of
:mod:`avocado.core.tree.TreeNode` with the params.

Varianter
~~~~~~~~~

:mod:`avocado.core.varianter.Varianter`

Is an internal object which is used to interact with the variants mechanism
in Avocado. It's lifecycle is compound of two stages. First it allows
the core/plugins to inject default values, then it is parsed and
only allows querying for values, number of variants and such.

Example workflow of `avocado run passtest.py -m example.yaml` is::

   avocado run passtest.py -m example.yaml
     |
     + parser.finish -> Varianter.__init__  // dispatcher initializes all plugins
     |
     + $PLUGIN -> args.default_avocado_params.add_default_param  // could be used to insert default values
     |
     + job.run_tests -> Varianter.is_parsed
     |
     + job.run_tests -> Varianter.parse
     |                     // processes default params
     |                     // initializes the plugins
     |                     // updates the default values
     |
     + job._log_variants -> Varianter.to_str  // prints the human readable representation to log
     |
     + runner.run_suite -> Varianter.get_number_of_tests
     |
     + runner._iter_variants -> Varianter.itertests  // Yields variants

In order to allow force-updating the `Varianter`_ it supports
``ignore_new_data``, which can be used to ignore new data. This is used
by :doc:`Replay` to replace the current run `Varianter`_ with the one
loaded from the replayed job. The workflow with ``ignore_new_data`` could
look like this::

   avocado run --replay latest -m example.yaml
     |
     + $PLUGIN -> args.default_avocado_params.add_default_param  // could be used to insert default values
     |
     + replay.run -> Varianter.is_parsed
     |
     + replay.run  // Varianter object is replaced with the replay job's one
     |             // Varianter.ignore_new_data is set
     |
     + $PLUGIN -> args.default_avocado_params.add_default_param  // is ignored as new data are not accepted
     |
     + job.run_tests -> Varianter.is_parsed
     |
     + job._log_variants -> Varianter.to_str
     |
     + runner.run_suite -> Varianter.get_number_of_tests
     |
     + runner._iter_variants -> Varianter.itertests

The `Varianter`_ itself can only produce an empty variant with the
`Default params`_, but it invokes all `Varianter plugins`_ and if any
of them reports variants it yields them instead of the default variant.



Default params
~~~~~~~~~~~~~~

Unlike `Test's default params`_ the `Default params`_ is a mechanism to
specify default values in `Varianter`_ or `Varianter plugins`_. Their
purpose is usually to define values dependent on the system which should
not affect the test's results. One example is a qemu binary location
which might differ from one host to another host, but in the end
they should result in qemu being executable in test. For this reason
the `Default params`_ do not affects the test's variant-id (at least
not in the official `Varianter plugins`_).

These params can be set from plugin/core by getting ``default_avocado_params``
from ``args`` and using::

    default_avocado_params.add_default_parma(self, name, key, value, path=None)

Where:

* name - name of the plugin which injects data (not yet used for anything,
  but we plan to allow white/black listing)
* key - the parameter's name
* value - the parameter's value
* path - the location of this parameter. When the path does not exists yet,
  it's created out of `TreeNode`_.

Varianter plugins
~~~~~~~~~~~~~~~~~

:mod:`avocado.core.plugin_interfaces.VarianterPlugin`

A plugin interface that can be used to build custom plugins which
are used by `Varianter`_ to get test variants. For inspiration see
:mod:`avocado.plugins.yaml_to_mux.YamlToMux` which is in-core
implementation of a multiplex varianter plugin and which is
described in `Yaml_to_mux plugin`_.

Multiplexer
~~~~~~~~~~~

:mod:`avocado.core.mux`

``Multiplexer`` or simply ``Mux`` is an abstract concept, which was
the basic idea behind the tree-like params structure with the support
to produce all possible variants. There is a core implementation of
basic building blocks that can be used when creating a custom plugin.
There is a demonstration version of plugin using this concept in
:mod:`avocado.plugins.yaml_to_mux` which adds a parser and then
uses this multiplexer concept to define an avocado plugin to produce
variants from ``yaml`` (or ``json``) files.


Multiplexer concept
===================

As mentioned earlier, this is an in-core implementation of building
blocks intended for writing `Varianter plugins`_ based on a tree
with `Multiplex domains`_ defined. The available blocks are:

* `MuxTree`_ - Object which represents a part of the tree and handles
  the multiplexation, which means producing all possible variants
  from a tree-like object.
* `MuxPlugin`_ - Base class to build `Varianter plugins`_
* ``MuxTreeNode`` - Inherits from `TreeNode`_ and adds the support for
  control flags (``MuxTreeNode.ctrl``) and multiplex domains
  (``MuxTreeNode.multiplex``).

And some support classes and methods eg. for filtering and so on.

Multiplex domains
~~~~~~~~~~~~~~~~~

A default `AvocadoParams`_ tree with variables could look like this::

   Multiplex tree representation:
    ┣━━ paths
    ┃     → tmp: /var/tmp
    ┃     → qemu: /usr/libexec/qemu-kvm
    ┗━━ environ
        → debug: False

The multiplexer wants to produce similar structure, but also to be able
to define not just one variant, but to define all possible combinations
and then report the slices as variants. We use the term
`Multiplex domains`_ to define that children of this node are not just
different paths, but they are different values and we only want one at
a time. In the representation we use double-line to visibily distinguish
between normal relation and multiplexed relation. Let's modify our
example a bit::

   Multiplex tree representation:
    ┣━━ paths
    ┃     → tmp: /var/tmp
    ┃     → qemu: /usr/libexec/qemu-kvm
    ┗━━ environ
         ╠══ production
         ║     → debug: False
         ╚══ debug
               → debug: True

The difference is that ``environ`` is now a ``multiplex`` node and it's
children will be yielded one at a time producing two variants::

   Variant 1:
    ┣━━ paths
    ┃     → tmp: /var/tmp
    ┃     → qemu: /usr/libexec/qemu-kvm
    ┗━━ environ
         ┗━━ production
               → debug: False
   Variant 2:
    ┣━━ paths
    ┃     → tmp: /var/tmp
    ┃     → qemu: /usr/libexec/qemu-kvm
    ┗━━ environ
         ┗━━ debug
               → debug: False

Note that the ``multiplex`` is only about direct children, therefore
the number of leaves in variants might differ::

   Multiplex tree representation:
    ┣━━ paths
    ┃     → tmp: /var/tmp
    ┃     → qemu: /usr/libexec/qemu-kvm
    ┗━━ environ
         ╠══ production
         ║     → debug: False
         ╚══ debug
              ┣━━ system
              ┃     → debug: False
              ┗━━ program
                    → debug: True

Produces one variant with ``/paths`` and ``/environ/production`` and
other variant with ``/paths``, ``/environ/debug/system`` and
``/environ/debug/program``.

As mentioned earlier the power is not in producing one variant, but
in defining huge scenarios with all possible variants. By using
tree-structure with multiplex domains you can avoid most of the
ugly filters you might know from Jenkin's sparse matrix jobs.
For comparison let's have a look at the same example in avocado::

   Multiplex tree representation:
    ┗━━ os
         ┣━━ distro
         ┃    ┗━━ redhat
         ┃         ╠══ fedora
         ┃         ║    ┣━━ version
         ┃         ║    ┃    ╠══ 20
         ┃         ║    ┃    ╚══ 21
         ┃         ║    ┗━━ flavor
         ┃         ║         ╠══ workstation
         ┃         ║         ╚══ cloud
         ┃         ╚══ rhel
         ┃              ╠══ 5
         ┃              ╚══ 6
         ┗━━ arch
              ╠══ i386
              ╚══ x86_64

Which produces::

   Variant 1:    /os/distro/redhat/fedora/version/20, /os/distro/redhat/fedora/flavor/workstation, /os/arch/i386
   Variant 2:    /os/distro/redhat/fedora/version/20, /os/distro/redhat/fedora/flavor/workstation, /os/arch/x86_64
   Variant 3:    /os/distro/redhat/fedora/version/20, /os/distro/redhat/fedora/flavor/cloud, /os/arch/i386
   Variant 4:    /os/distro/redhat/fedora/version/20, /os/distro/redhat/fedora/flavor/cloud, /os/arch/x86_64
   Variant 5:    /os/distro/redhat/fedora/version/21, /os/distro/redhat/fedora/flavor/workstation, /os/arch/i386
   Variant 6:    /os/distro/redhat/fedora/version/21, /os/distro/redhat/fedora/flavor/workstation, /os/arch/x86_64
   Variant 7:    /os/distro/redhat/fedora/version/21, /os/distro/redhat/fedora/flavor/cloud, /os/arch/i386
   Variant 8:    /os/distro/redhat/fedora/version/21, /os/distro/redhat/fedora/flavor/cloud, /os/arch/x86_64
   Variant 9:    /os/distro/redhat/rhel/5, /os/arch/i386
   Variant 10:    /os/distro/redhat/rhel/5, /os/arch/x86_64
   Variant 11:    /os/distro/redhat/rhel/6, /os/arch/i386
   Variant 12:    /os/distro/redhat/rhel/6, /os/arch/x86_64

Versus Jenkin's sparse matrix::

   os_version = fedora20 fedora21 rhel5 rhel6
   os_flavor = none workstation cloud
   arch = i386 x86_64

   filter = ((os_version == "rhel5").implies(os_flavor == "none") &&
             (os_version == "rhel6").implies(os_flavor == "none")) &&
            !(os_version == "fedora20" && os_flavor == "none") &&
            !(os_version == "fedora21" && os_flavor == "none")

Which is still relatively simple example, but it grows dramatically with
inner-dependencies.

MuxPlugin
~~~~~~~~~

:mod:`avocado.core.mux.MuxPlugin`

Defines the full interface required by
:mod:`avocado.core.plugin_interfaces.VarianterPlugin`. The plugin writer
should inherit from this ``MuxPlugin``, then from the ``VarianterPlugin``
and call the::

   self.initialize_mux(root, mux_path, debug)

Where:

* root - is the root of your params tree (compound of `TreeNode`_ -like
  nodes)
* mux_path - is the `Mux path`_ to be used in test with all variants
* debug - whether to use debug mode (requires the passed tree to be
  compound of ``TreeNodeDebug``-like nodes which stores the origin
  of the variant/value/environment as the value for listing purposes
  and is __NOT__ intended for test execution.

This method must be called before the `Varianter`_'s second stage
(the latest opportunity is during ``self.update_defaults``). The
`MuxPlugin`_'s code will take care of the rest.

MuxTree
~~~~~~~

This is the core feature where the hard work happens. It walks the tree
and remembers all leaf nodes or uses list of `MuxTrees` when another
multiplex domain is reached while searching for a leaf.

When it's asked to report variants, it combines one variant of each
remembered item (leaf node always stays the same, but `MuxTree` circles
through it's values) which recursively produces all possible variants
of different `multiplex domains`_.

Yaml_to_mux plugin
==================

:mod:`avocado.plugins.yaml_to_mux`

So far everything was a bit theoretical, let's use examples to describe
how the multiplexation works on a ``yaml_to_mux`` plugin. This plugin
inherits from the :mod:`avocado.core.mux.MuxPlugin` and the only
thing it implements is the argument parsing to get some input
and a custom ``yaml`` parser (which is also capable of parsing ``json``).

The ``yaml`` file is perfect for this task as it's easily read by
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
This means that the value can be of any YAML supported value, eg. bool, None,
list or custom type, while the key is always string.

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
specify custom resolution order or you are specifying non-test parameters, for
example parameters for your plugin, which you need to separate from the test
parameters.


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
