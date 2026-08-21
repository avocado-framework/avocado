========================
113.0 - TBD
========================

The Avocado team is proud to present another release: Avocado 113.0,
AKA "TBD", is now available!

Release documentation: `Avocado 113.0
<http://avocado-framework.readthedocs.io/en/113.0/>`_

Users/Test Writers
==================

* The Podman spawner now bootstraps Avocado from a single universal
  wheel (``avocado_framework-{version}-py3-none-any.whl``) instead of
  per-CPython eggs plus setuptools 59.2.  The wheel is unpacked on the
  host and bind-mounted read-only at ``/opt/avocado-wheel``.  This
  unblocks Fedora 39+ / Python 3.12+ images (GitHub issues `#6108
  <https://github.com/avocado-framework/avocado/issues/6108>`_ and
  `#6115 <https://github.com/avocado-framework/avocado/issues/6115>`_).
  Use ``--spawner-podman-avocado-wheel``; ``--spawner-podman-avocado-egg``
  remains as a deprecated alias.  The container image must provide
  ``python3``; Fedora 41+ default container images no longer do, so
  selftests use ``fedora:40``.  ``fedora-toolbox`` images still include
  a current interpreter.

* Avocado no longer builds or publishes Python eggs.  Releases upload
  ``py3-none-any`` wheels to GitHub (and PyPI, as before).  Isolated
  spawners fetch that wheel from GitHub, then fall back to PyPI if the
  GitHub asset is missing (Avocado 113.0 and earlier only attached
  eggs).  The ``setuptools<82`` install workaround is no longer
  required for Avocado itself.

Utility Modules
===============

*

Bug Fixes
=========

*

Internal changes
================

* CI dropped the per-interpreter ``egg-build`` matrix.  The release
  pipeline publishes wheels to GitHub instead of eggs.

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
