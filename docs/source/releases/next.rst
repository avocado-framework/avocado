========================
113.0 - TBD
========================

The Avocado team is proud to present another release: Avocado 113.0,
AKA "TBD", is now available!

Release documentation: `Avocado 113.0
<http://avocado-framework.readthedocs.io/en/113.0/>`_

Users/Test Writers
==================

*

Utility Modules
===============

*

Bug Fixes
=========

* The Podman spawner now resolves the default ``podman`` binary through
  ``PATH``, supporting installations outside ``/usr/bin``.
* :func:`avocado.utils.nvme.get_ns_status` now handles nvme-cli builds
  that reject a controller node argument to ``nvme show-topology``, and
  correctly resolves namespace status for peer controllers in multi-path
  subsystems (e.g. ``nvme0`` and ``nvme3`` both serving ``nvme3n1``).
  A whole-system ``nvme show-topology -o json`` fallback is used when
  the controller-addressed form fails or yields no match.

Internal changes
================

*

Additional information
======================

For more information, please check out the complete
`Avocado changelog
<https://github.com/avocado-framework/avocado/compare/112.0...113.0>`_.

For more information on the actual issues addressed, please check out
the `milestone information
<https://github.com/avocado-framework/avocado/milestone/39>`_.

For more information on the release codename, please refer to `IMDb
<TBD>`_.
