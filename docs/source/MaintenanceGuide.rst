.. _maintenance-guide:

=================
Releasing avocado
=================

So you have all PRs approved, the Sprint meeting is done and now
Avocado is ready to be released.  Great, let's go over (most of) the
details you need to pay attention to.

Bump the version number
=======================

For the Avocado versioning, two files need to receive a manual version update:

 * ``VERSION``
 * ``python-avocado.spec``

followed by ``make propagate-version`` to propagate this change to all
optional and "linkabe" plugins sharing the parent dir (eg. ``avocado-vt``).
Don't forget to commit the changes of "linked" plugins as they live in
different repositories.

An example diff (after the ``make propagate-version``) looks like this:

.. code-block:: diff

    diff --git a/VERSION b/VERSION
    index dd0353d..aafccd8 100644
    --- a/VERSION
    +++ b/VERSION
    @@ -1 +1 @@
    -48.0
    +49.0
    diff --git a/optional_plugins/html/VERSION b/optional_plugins/html/VERSION
    index dd0353d..aafccd8 100644
    --- a/optional_plugins/html/VERSION
    +++ b/optional_plugins/html/VERSION
    @@ -1 +1 @@
    -48.0
    +49.0
    diff --git a/optional_plugins/robot/VERSION b/optional_plugins/robot/VERSION
    index dd0353d..aafccd8 100644
    --- a/optional_plugins/robot/VERSION
    +++ b/optional_plugins/robot/VERSION
    @@ -1 +1 @@
    -48.0
    +49.0
    diff --git a/optional_plugins/runner_docker/VERSION b/optional_plugins/runner_docker/VERSION
    index dd0353d..aafccd8 100644
    --- a/optional_plugins/runner_docker/VERSION
    +++ b/optional_plugins/runner_docker/VERSION
    @@ -1 +1 @@
    -48.0
    +49.0
    diff --git a/optional_plugins/runner_remote/VERSION b/optional_plugins/runner_remote/VERSION
    index dd0353d..aafccd8 100644
    --- a/optional_plugins/runner_remote/VERSION
    +++ b/optional_plugins/runner_remote/VERSION
    @@ -1 +1 @@
    -48.0
    +49.0
    diff --git a/optional_plugins/runner_vm/VERSION b/optional_plugins/runner_vm/VERSION
    index dd0353d..aafccd8 100644
    --- a/optional_plugins/runner_vm/VERSION
    +++ b/optional_plugins/runner_vm/VERSION
    @@ -1 +1 @@
    -48.0
    +49.0
    diff --git a/python-avocado.spec b/python-avocado.spec
    index 6a4b067..4b9dba8 100644
    --- a/python-avocado.spec
    +++ b/python-avocado.spec
    @@ -12,7 +12,7 @@

     Summary: Framework with tools and libraries for Automated Testing
     Name: python-%{srcname}
    -Version: 48.0
    +Version: 49.0
     Release: 1%{?dist}
     License: GPLv2
     Group: Development/Tools
    @@ -259,6 +259,9 @@ examples of how to write tests on your own.
     %{_datadir}/avocado/wrappers

     %changelog
    +* Wed Apr 12 2017 Lukas Doktor <ldoktor@redhat.com> - 49.0-0
    +- Testing release
    +
     * Mon Apr  3 2017 Cleber Rosa <cleber@localhost.localdomain> - 48.0-1
     - Updated exclude directives and files for optional plugins

You can find on git such commits that will help you get oriented for other
repos.

Which repositories you should pay attention to
==============================================

In general, a release of avocado includes taking a look and eventually release
content in the following repositories:

* ``avocado``
* ``avocado-vt``

Tag all repositories
====================

When everything is in good shape, commit the version changes and tag
that commit in master with::

  $ git tag -u $(GPG_ID) -s $(RELEASE) -m 'Avocado Release $(RELEASE)'

Then the tag should be pushed to the GIT repository with::

  $ git push --tags

Build RPMs
==========

Go to the source directory and do::

    $ make rpm
    ...
    + exit 0

This should be all.  It will build packages using ``mock``, targeting
your default configuration.  That usually means the same platform
you're currently on.

Sign Packages
=============

All the packages should be signed for safer public consumption.  The
process is, of course, dependent on the private keys, put is based on
running::

  $ rpm --resign

For more information look at the ``rpmsign(8)`` man page.

Upload packages to repository
=============================

The current distribution method is based on serving content over HTTP.
That means that repository metadata is created locally and
synchronized to the well know public Web server.  A process similar
to::

  $ cd $REPO_ROOT && for DIR in epel-?-noarch fedora-??-noarch; \
  do cd $DIR && createrepo -v . && cd ..; done;

Creates the repo metadata locally.  Then a command similar to::

  $ rsync -va $REPO_ROOT user@repo_web_server:/path

Is used to copy the content over.


Write release notes
===================

Release notes give an idea of what has changed on a given development
cycle.  Good places to go for release notes are:

1) Git logs
2) Trello Cards (Look for the Done lists)
3) Github compare views: https://github.com/avocado-framework/avocado/compare/0.28.0...0.29.0

Go there and try to write a text that represents the changes that the
release encompasses.

Upload package to PyPI
======================

Users may also want to get Avocado from the PyPI repository, so please upload
there as well.  To help with the process, please run::

 $ make pypi

And follow the URL and brief instructions given.

Configure Read The Docs
=======================

On https://readthedocs.org/dashboard/avocado-framework/edit/:

 - Click in **Versions**. In **Choose Active Versions**, find the version
   you're releasing and check the **Active** option. **Submit**.
 - Click in **Versions** again. In **Default Version**, select the new
   version you're releasing. **Submit**.

Send e-mails to avocado-devel and other places
==============================================

Send the e-mail with the release notes to avocado-devel and
virt-test-devel.
