.. _lts_next:

============
The Next LTS
============

The Long Term Stability releases of Avocado are the result of the
accumulated changes on regular (non-LTS) releases.

This section tracks the changes introduced on each regular (non-LTS)
Avocado release, and gives a sneak preview of what will make into the
next LTS release.

What's new?
===========

When compared to the last LTS (69.x), the main changes to be
introduced by the next LTS version are:

Test Writers
------------

Test APIs
~~~~~~~~~

Utility APIs
~~~~~~~~~~~~

Users
-----

Output Plugins
~~~~~~~~~~~~~~

* Starting from this release, `--paginator` will be a global option. You
  should add this option before any sub-command. i.e.: `avocado
  --paginator off plugins`.

* Starting from this release, `--verbose` will be a global option. You
  should add this option before any sub-command. i.e.: `avocado
  --verbose list`.

Test Loader Plugins
~~~~~~~~~~~~~~~~~~~

Varianter Plugins
~~~~~~~~~~~~~~~~~

Test Runner Plugins
~~~~~~~~~~~~~~~~~~~

Complete list of changes
========================

For a complete list of changes between the last LTS release (52.0) and
this release, please check out `the Avocado commit changelog
<https://github.com/avocado-framework/avocado/compare/69.0...master>`_.
