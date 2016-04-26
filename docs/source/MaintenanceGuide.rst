.. _maintenance-guide:

=================
Releasing avocado
=================

So you have all PRs approved, the Sprint meeting is done and now
Avocado is ready to be released.  Great, let's go over (most of) the
details you need to pay attention to.

Bump the version number
=======================

Go through the avocado code base and update the release number. At the time
of this writing, the diff looked like this::

    diff --git a/avocado.spec b/avocado.spec
    index eb910e8..21313ca 100644
    --- a/avocado.spec
    +++ b/avocado.spec
    @@ -1,7 +1,7 @@
     Summary: Avocado Test Framework
     Name: avocado
    -Version: 0.28.0
    -Release: 2%{?dist}
    +Version: 0.29.0
    +Release: 0%{?dist}
     License: GPLv2
     Group: Development/Tools
     URL: http://avocado-framework.github.io/
    @@ -104,6 +104,9 @@ examples of how to write tests on your own.
     %{_datadir}/avocado/wrappers

     %changelog
    +* Wed Oct 7 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.29.0-0
    +- New upstream release 0.29.0
    +
     * Wed Sep 16 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.28.0-2
     - Add pystache, aexpect, psutil, sphinx and yum/dnf dependencies for functional/unittests

    diff --git a/avocado/core/version.py b/avocado/core/version.py
    index c927b19..a555af5 100755
    --- a/avocado/core/version.py
    +++ b/avocado/core/version.py
    @@ -18,7 +18,7 @@ __all__ = ['MAJOR', 'MINOR', 'RELEASE', 'VERSION']


     MAJOR = 0
    -MINOR = 28
    +MINOR = 29
     RELEASE = 0

     VERSION = "%s.%s.%s" % (MAJOR, MINOR, RELEASE)
    diff --git a/setup.cfg b/setup.cfg
    index 76953b9..5cf90e9 100644
    --- a/setup.cfg
    +++ b/setup.cfg
    @@ -1,6 +1,6 @@
     [metadata]
     name = avocado
    -version = 0.28.0
    +version = 0.29.0
     summary = Avocado Test Framework
     description-file =
         README.rst

You can find on git such commits that will help you get oriented for other
repos.

Which repositories you should pay attention to
==============================================

In general, a release of avocado includes taking a look and eventually release
content in the following repositories:

* ``avocado``
* ``avocado-vt``
* ``avocado-virt``
* ``avocado-virt-tests``

In this order of importance. Some times ``avocado-virt`` and ``avocado-virt-tests``
might not get updates, so it's OK to skip them.

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

Send e-mails to avocado-devel and other places
==============================================

Send the e-mail with the release notes to avocado-devel and
virt-test-devel.
