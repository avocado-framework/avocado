.. _mutliplexer:

Multiplexer
===========

:mod:`avocado_varianter_yaml_to_mux.mux`

``Multiplexer`` or simply ``Mux`` is an abstract concept, which was
the basic idea behind the tree-like params structure with the support
to produce all possible variants. There is a core implementation of
basic building blocks that can be used when creating a custom plugin.
There is a demonstration version of plugin using this concept in
:mod:`avocado_varianter_yaml_to_mux`
which adds a parser and then
uses this multiplexer concept to define an Avocado plugin to produce
variants from ``yaml`` (or ``json``) files.


Multiplexer concept
===================

As mentioned earlier, this is an in-core implementation of building
blocks intended for writing :ref:`varianter-plugins` based on a tree
with `Multiplex domains`_ defined. The available blocks are:

* `MuxTree`_ - Object which represents a part of the tree and handles
  the multiplexation, which means producing all possible variants
  from a tree-like object.
* `MuxPlugin`_ - Base class to build :ref:`varianter-plugins`
* ``MuxTreeNode`` - Inherits from :ref:`tree-node` and adds the support for
  control flags (``MuxTreeNode.ctrl``) and multiplex domains
  (``MuxTreeNode.multiplex``).

And some support classes and methods eg. for filtering and so on.

Multiplex domains
~~~~~~~~~~~~~~~~~

A default `avocado-params` tree with variables could look like this::

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
For comparison let's have a look at the same example in Avocado::

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

:class:`avocado_varianter_yaml_to_mux.mux.MuxPlugin`

Defines the full interface required by
:class:`avocado.core.plugin_interfaces.Varianter`. The plugin writer
should inherit from this ``MuxPlugin``, then from the ``Varianter``
and call the::

   self.initialize_mux(root, paths, debug)

Where:

* root - is the root of your params tree (compound of :ref:`tree-node` -like
  nodes)
* paths - is the :ref:`parameter-paths` to be used in test with all variants
* debug - whether to use debug mode (requires the passed tree to be
  compound of ``TreeNodeDebug``-like nodes which stores the origin
  of the variant/value/environment as the value for listing purposes
  and is __NOT__ intended for test execution.

This method must be called before the :ref:`varianter`'s second
stage. The `MuxPlugin`_'s code will take care of the rest.

MuxTree
~~~~~~~

This is the core feature where the hard work happens. It walks the tree
and remembers all leaf nodes or uses list of `MuxTrees` when another
multiplex domain is reached while searching for a leaf.

When it's asked to report variants, it combines one variant of each
remembered item (leaf node always stays the same, but `MuxTree` circles
through it's values) which recursively produces all possible variants
of different `multiplex domains`_.
