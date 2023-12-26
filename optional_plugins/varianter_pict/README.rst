.. _varianter_pict:

PICT Varianter plugin
=====================

:mod:`avocado_varianter_pict`

This plugin uses a third-party tool to provide variants created by
"Pair-Wise" algorithms, also known as Combinatorial Independent
Testing.

Installing PICT
---------------

PICT is a free software (MIT licensed) tool that implements
combinatorial testing.  More information about it can be found at
https://github.com/Microsoft/pict/ .

If you're building from sources, make sure you have a C++ compiler
such as GCC or clang, and make.  The included ``Makefile`` should
work out of the box and give you a ``pict`` binary.

Then copy the ``pict`` binary to a location in your ``$PATH``.
Alternatively, you may use the plugin ``--pict-binary`` command line
option to provide a specific location of the pict binary, but that
is not as convenient as having it on your ``$PATH``.

Using the PICT Varianter Plugin
-------------------------------

To install the Avocado PICT plugin from pip, use::

    $ sudo pip install avocado-framework-plugin-varianter-pict

To run the example below, use the test included in the avocado code ::

    $ git clone https://github.com/avocado-framework/avocado.git

The following listing is a sample (simple) PICT file included
at ``avocado/examples/varianter_pict/params.pict`` ::

    arch: intel, amd
    block_driver: scsi, ide, virtio
    net_driver: rtl8139, e1000, virtio
    guest: windows, linux
    host: rhel6, rhel7, rhel8

To list the variants generated with the default combination order (2,
that is, do a pairwise idenpendent combinatorial testing)::

  $ avocado variants --pict-parameter-file=avocado/examples/varianter_pict/params.pict
  Pict Variants (11):
  Variant amd-scsi-rtl8139-windows-rhel6-acff:    /run
  Variant intel-scsi-virtio-linux-rhel8-26df:    /run
  Variant amd-ide-virtio-windows-rhel7-3fe7:    /run
  Variant amd-virtio-e1000-linux-rhel7-bf2d:    /run
  Variant intel-scsi-e1000-windows-rhel8-4808:    /run
  Variant intel-scsi-rtl8139-linux-rhel7-2975:    /run
  Variant intel-virtio-rtl8139-windows-rhel8-6632:    /run
  Variant intel-ide-rtl8139-linux-rhel6-edd2:    /run
  Variant intel-virtio-virtio-windows-rhel6-e95a:    /run
  Variant amd-ide-e1000-linux-rhel8-5fcc:    /run
  Variant amd-ide-e1000-linux-rhel6-eb43:    /run

To list the variants generated with a 3-way combination::

  $ avocado variants --pict-parameter-file=avocado/examples/varianter_pict/params.pict \
    --pict-order-of-combinations=3

  Pict Variants (28):
  Variant intel-ide-virtio-windows-rhel7-aea5:    /run
  ...skip...
  Variant intel-scsi-e1000-linux-rhel7-9f61:    /run

To run tests, just replace the ``variants`` avocado command for ``run``::

  $ avocado run --pict-parameter-file=avocado/examples/varianter_pict/params.pict /bin/true

The tests given in the command line should then be executed with all
variants produced by the combinatorial algorithm implemented by PICT.
