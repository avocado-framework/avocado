.. _test-parameters:

===============
Test parameters
===============

.. note:: This section describes in detail what test parameters are and how
   the whole variants mechanism works in Avocado. If you're interested in the
   basics, see :ref:`accessing-test-parameters` or practical view by examples
   in :ref:`yaml-to-mux-plugin`.

Avocado allows passing parameters to tests, which effectively results in
several different variants of each test. These parameters are available in
(test's) ``self.params`` and are of
:class:`avocado.core.varianter.AvocadoParams` type.

The data for ``self.params`` are supplied by
:class:`avocado.core.varianter.Varianter` which asks all registered plugins
for variants or uses default when no variants are defined.

Overall picture of how the params handling works is:

.. following figure is not really a C code, but it renders well and it
   increases the visibility.

.. code-block:: c

       +-----------+
       |           |  // Test uses AvocadoParams, with content either from
       |   Test    |  // a variant or from the test parameters given by
       |           |  // "--test-parameters"
       +-----^-----+
             |
             |
       +-----------+
       |  Runner   |  // iterates through tests and variants to run all
       +-----^-----+  // desired combinations specified by "--execution-order".
             |        // if no variants are produced by varianter plugins,
             |        // use the test parameters given by "--test-parameters"
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

TreeNode
~~~~~~~~

:class:`avocado.core.tree.TreeNode`

Is a node object allowing to create tree-like structures with
parent->multiple_children relations and storing params. It can
also report it's environment, which is set of params gathered
from root to this node. This is used in tests where instead of
passing the full tree only the leaf nodes are passed and their
environment represents all the values of the tree.

AvocadoParams
~~~~~~~~~~~~~

:class:`avocado.core.varianter.AvocadoParams`

Is a "database" of params present in every (instrumented) avocado
test.  It's produced during :class:`avocado.core.test.Test`'s
``__init__`` from a `variant`_. It accepts a list of `TreeNode`_
objects; test name :class:`avocado.core.test.TestID` (for logging
purposes) and a list of default paths (`Parameter Paths`_).

In test it allows querying for data by using::

   self.params.get($name, $path=None, $default=None)

Where:

* name - name of the parameter (key)
* path - where to look for this parameter (when not specified uses mux-path)
* default - what to return when param not found

Each `variant`_ defines a hierarchy, which is preserved so `AvocadoParams`_
follows it to return the most appropriate value or raise Exception on error.

Parameter Paths
~~~~~~~~~~~~~~~

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
parameter paths to ``["/downstream/*", "/upstream/*"]`` to make all relative
calls (path starting with ``*``) to first look in nodes in ``/downstream``
and if not found look into ``/upstream``.

More practical overview of parameter paths is in :ref:`yaml-to-mux-plugin`
in :ref:`yaml-to-mux-resolution-order` section.

Variant
~~~~~~~

Variant is a set of params produced by `Varianter`_s and passed to the
test by the test runner as ``params`` argument. The simplest variant
is ``None``, which still produces an empty `AvocadoParams`_. Also, the
`Variant`_ can also be a ``tuple(list, paths)`` or just the
``list`` of :class:`avocado.core.tree.TreeNode` with the params.

Dumping/Loading Variants
~~~~~~~~~~~~~~~~~~~~~~~~

Depending on the number of parameters, generating the Variants can be very
compute intensive. As the Variants are generated as part of the Job execution,
that compute intensive task will be executed by the systems under test, causing
a possibly unwanted cpu load on those systems.

To avoid such situation, you can acquire the resulting JSON serialized variants
file, generated out of the variants computation, and load that file on the
system where the Job will be executed.

There are two ways to acquire the JSON serialized variants file:

- Using the ``--json-variants-dump`` option of the ``avocado variants``
  command::

    $ avocado variants --mux-yaml examples/yaml_to_mux/hw/hw.yaml --json-variants-dump variants.json
    ...

    $ file variants.json
    variants.json: ASCII text, with very long lines, with no line terminators

- Getting the auto-generated JSON serialized variants file after a Avocado Job
  execution::

    $ avocado run passtest.py --mux-yaml examples/yaml_to_mux/hw/hw.yaml
    ...

    $ file $HOME/avocado/job-results/latest/jobdata/variants.json
    $HOME/avocado/job-results/latest/jobdata/variants.json: ASCII text, with very long lines, with no line terminators

Once you have the ``variants.json`` file, you can load it on the system where
the Job will take place::

   $ avocado run passtest.py --json-variants-load variants.json
   JOB ID     : f2022736b5b89d7f4cf62353d3fb4d7e3a06f075
   JOB LOG    : $HOME/avocado/job-results/job-2018-02-09T14.39-f202273/job.log
    (1/6) passtest.py:PassTest.test;intel-scsi-56d0: PASS (0.04 s)
    (2/6) passtest.py:PassTest.test;intel-virtio-3d4e: PASS (0.02 s)
    (3/6) passtest.py:PassTest.test;amd-scsi-fa43: PASS (0.02 s)
    (4/6) passtest.py:PassTest.test;amd-virtio-a59a: PASS (0.02 s)
    (5/6) passtest.py:PassTest.test;arm-scsi-1c14: PASS (0.03 s)
    (6/6) passtest.py:PassTest.test;arm-virtio-5ce1: PASS (0.04 s)
   RESULTS    : PASS 6 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
   JOB TIME   : 0.51 s
   JOB HTML   : $HOME/avocado/job-results/job-2018-02-09T14.39-f202273/results.html

Varianter
~~~~~~~~~

:class:`avocado.core.varianter.Varianter`

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

The `Default params`_ is a mechanism to specify default values in
`Varianter`_ or `Varianter plugins`_. Their purpose is usually to
define values dependent on the system which should not affect the
test's results. One example is a qemu binary location which might
differ from one host to another host, but in the end they should
result in qemu being executable in test. For this reason the `Default
params`_ do not affects the test's variant-id (at least not in the
official `Varianter plugins`_).

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

Test parameters
~~~~~~~~~~~~~~~

This is an Avocado core feature, that is, it's not dependent on any
varianter plugin.  In fact, it's only active when no Varianter plugin
is used and produces a valid variant.

Avocado will use those simple parameters, and will pass them to all
tests in a job execution.  This is done on the command line via
``--test-parameters``, or simply, ``-p``.  It can be given multiple
times for multiple parameters.

Because Avocado parameters do not have a mechanism to define their
types, test code should always consider that a parameter value is a
string, and convert it to the appropriate type.

.. note:: Some varianter plugins would implicitly set parameters
   with different data types, but given that the same test can be
   used with different, or none, varianter plugins, it's safer if
   the test does an explicit check or type conversion.

Because the :class:`avocado.core.varianter.AvocadoParams` mandates the
concept of a parameter path (a legacy of the tree based Multiplexer)
and these test parameters are flat, those test parameters are placed
in the ``/`` path.  This is to ensure maximum compatibility with tests
that do not choose an specific parameter location.

Varianter plugins
~~~~~~~~~~~~~~~~~

:class:`avocado.core.plugin_interfaces.Varianter`

A plugin interface that can be used to build custom plugins which
are used by `Varianter`_ to get test variants. For inspiration see
:class:`avocado_varianter_yaml_to_mux.YamlToMux` which is an
optional varianter plugin. Details about this plugin can be
found here :ref:`yaml-to-mux-plugin`.

Multiplexer
~~~~~~~~~~~

:mod:`avocado.core.mux`

``Multiplexer`` or simply ``Mux`` is an abstract concept, which was
the basic idea behind the tree-like params structure with the support
to produce all possible variants. There is a core implementation of
basic building blocks that can be used when creating a custom plugin.
There is a demonstration version of plugin using this concept in
:mod:`avocado_varianter_yaml_to_mux`
which adds a parser and then
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

:class:`avocado.core.mux.MuxPlugin`

Defines the full interface required by
:class:`avocado.core.plugin_interfaces.Varianter`. The plugin writer
should inherit from this ``MuxPlugin``, then from the ``Varianter``
and call the::

   self.initialize_mux(root, paths, debug)

Where:

* root - is the root of your params tree (compound of `TreeNode`_ -like
  nodes)
* paths - is the `Parameter paths`_ to be used in test with all variants
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
