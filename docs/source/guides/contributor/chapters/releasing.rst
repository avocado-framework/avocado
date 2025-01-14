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

How to refresh Fedora rawhide
-----------------------------

This is an outline of the steps to update the Fedora rawhide packages.
This example is based on updating from 82.0 to 83.0.

Update downstream python-avocado package
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. Use pagure to create a personal fork of the downstream Fedora dist-git
   ``python-avocado`` package source repository
   https://src.fedoraproject.org/rpms/python-avocado
   if you don’t already have one.

#. Clone your personal fork repository to your local workspace.

#. Checkout the ``latest`` branch, and make sure your ``latest``
   branch is in sync with the most recent commits from the official
   dist-git repo you forked from.

#. Locate the official upstream commit hash and date corresponding to the
   upstream GitHub release tag.
   (eg., https://github.com/avocado-framework/avocado/releases/tag/75.1)
   Use those values to update the ``%global commit`` and ``%global commit_date``
   lines in the downstream ``python-avocado.spec`` file.

#. Update the ``Version:`` line with the new release tag.

#. Reset the ``Release:`` line to ``1%{?gitrel}%{?dist}``.

#. Add a new entry at the beginning of the ``%changelog`` section with a message
   similar to ``Sync with upstream release 83.0.``.

#. See what changed in the upstream SPEC file since the last release.
   You can do this by comparing branches on GitHub
   (eg., https://github.com/avocado-framework/avocado/compare/82.0..83.0)
   and searching for ``python-avocado.spec``.
   If there are changes beyond just the
   ``%global commit``, ``%global commit_date``, and ``Version:`` lines,
   and the ``%changelog`` section,
   make any necessary corresponding changes to the downstream SPEC file.
   Note: the commit hash in the upstream SPEC file *will* be different that
   what gets put in the downstream SPEC file since the upstream hash was added
   to the file before the released commit was made.
   Add an additional note to your ``%changelog`` message if there were any
   noteworthy changes.

#. Download the new upstream source tarball based on the updated SPEC by
   running::

    spectool -g python-avocado.spec

#. Add the new source tarball to the dist-git lookaside cache and update your
   local repo by running::

    fedpkg new-sources avocado-83.0.tar.gz

#. Create a Fedora source RPM from the updated SPEC file and tarball by running::

    fedpkg --release f33 srpm

   It should write an SRPM file (eg., ``python-avocado-83.0-1.fc33.src.rpm``)
   to the current directory.

#. Test build the revised package locally using ``mock``.  Run the
   build using the same Fedora release for which the SRPM was
   created::

    mock -r fedora-33-x86_64 python-avocado-83.0-1.fc33.src.rpm

#. If the package build fails, go back and fix the SPEC file, re-create the SRPM,
   and retry the mock build.
   It is occasionally necessary to create a patch to disable specific tests
   or pull in some patches from upstream to get the package to build correctly.
   See https://src.fedoraproject.org/rpms/python-avocado/tree/69lts as an example.

#. Repeat the SRPM generation and mock build for all other supported Fedora
   releases, Fedora Rawhide, and the applicable EPEL (currently EPEL8).

#. When you have successful builds for all releases,
   ``git add``, ``git commit``, and ``git push`` your updates.
