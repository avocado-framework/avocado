.. _maintenance-guide:

=================
Releasing avocado
=================

So you have all PRs approved, and Sprint meeting is done and now avocado is ready to be released.
Great, let's go over (most of) the details you need to pay attention to.

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
    +Release: 1%{?dist}
     License: GPLv2
     Group: Development/Tools
     URL: http://avocado-framework.github.io/
    @@ -104,6 +104,9 @@ examples of how to write tests on your own.
     %{_datadir}/avocado/wrappers

     %changelog
    +* Wed Oct 7 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.29.0-1
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

Build source rpms
=================

Go to the source directory and do::

    $ make build-rpm-all
    ...
    + exit 0


Upload source to a public location
==================================

Upload the source RPMs to a public URL, for building with COPR::

    $ scp SRPMS/avocado-0.29.0-1.fc22.src.rpm user@remote.box:/path/to/srcrpms

Send the packages to build on COPR
==================================

Then go to COPR, and give the public URL of the srcrpm package to the new build
tab (you must be logged into FAS - Fedora Accounts System). For the COPR
lmr/Autotest, the new build tab will be located in:

https://copr.fedoraproject.org/coprs/lmr/Autotest/add_build/

Give the RPM URL to that dialog, select all the chroots where the package will be
built, then watch for build problems.

If everything went well, great! Some times though, you'll have to go through the
COPR build errors to figure out what is wrong. Hint - It's frequently something
related to build or runtime dependencies that we forgot to add at the build
time. Remember that unittests now run by default in many of the chroots there,
so keep that in mind and search through the COPR logs. Keep working on the issues
until you get them all fixed.

Sometimes, particularly for not-released-yet
distros, the problem might be that one of our dependent packages was still
not built for that distro, or it's a package dependency issue that is being
worked out, and it's not avocado's fault. The best you can do in that case is to
disable the build on that particular distro.

Keep working until all the builds are passing.

Tag all repositories
====================

When everything is in good shape, commit the version changes and tag that commit
in master with::

    $ git tag -u $(GPG_ID) -s $(RELEASE) -m 'Avocado Release $(RELEASE)'

Write release notes
===================

Release notes give an idea of what has changed on a given development cycle.
Good places to go for release notes are:

1) Git logs
2) Trello Cards (Look for the Done lists)
3) Github compare views: https://github.com/avocado-framework/avocado/compare/0.28.0...0.29.0

Go there and try to write a text that represents the changes that the release encompasses

Send e-mails to avocado-devel and other places
==============================================

Send the e-mail with the release notes to avocado-devel and virt-test-devel.