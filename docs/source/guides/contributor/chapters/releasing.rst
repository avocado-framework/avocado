Releasing Avocado
=================

So you have all PRs approved, the Sprint meeting is done and now Avocado is
ready to be released.  Great, let's go over (most of) the details you need to
pay attention to.

Which repositories you should pay attention to
----------------------------------------------

In general, a release of Avocado includes taking a look and eventually release
content in the following repositories:

* ``avocado``
* ``avocado-vt``

How to release?
---------------

All the necessary steps are in JSON "testplans" to be executed with the
following commands::

  $ scripts/avocado-run-testplan -t examples/testplans/release/pre.json
  $ scripts/avocado-run-testplan -t examples/testplans/release/release.json

Just follow the steps and have a nice release!
