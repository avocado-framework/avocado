.. _maintenance-guide:

=================
Releasing avocado
=================

So you have all PRs approved, the Sprint meeting is done and now
Avocado is ready to be released.  Great, let's go over (most of) the
details you need to pay attention to.

Bump the version number
=======================

For the core Avocado versioning, two files need to receive a version update:

 * ``VERSION``
 * ``python-avocado.spec``

So, go through the Avocado code base and update the version number. At
the time of this writing, the diff looks like this:

.. code-block:: diff

    diff --git a/VERSION b/VERSION
    index 98bc1f4..dd0353d 100644
    --- a/VERSION
    +++ b/VERSION
    @@ -1 +1 @@
    -47.0
    +48.0
    diff --git a/python-avocado.spec b/python-avocado.spec
    index 7071805..483ebce 100644
    --- a/python-avocado.spec
    +++ b/python-avocado.spec
    @@ -6,8 +6,8 @@

     Summary: Framework with tools and libraries for Automated Testing
     Name: python-%{srcname}
    -Version: 47.0
    -Release: 1%{?dist}
    +Version: 48.0
    +Release: 0%{?dist}
     License: GPLv2
     Group: Development/Tools
     URL: http://avocado-framework.github.io/
    @@ -211,6 +211,9 @@ examples of how to write tests on your own.
     %{_datadir}/avocado/wrappers

     %changelog
    +* Mon Apr  3 2017 Cleber Rosa <cleber@redhat.com> - 48.0-0
    +- New upstream release
    +
     * Wed Mar  8 2017 Cleber Rosa <cleber@redhat.com> - 47.0-1
     - Rename package to python-avocado and subpackges accordingly

Then, for all the optional plugins, the version number on their
``setup.py`` files also needs to be bumped.  Currently, the diff looks
like this:

.. code-block:: diff

    diff --git a/optional_plugins/html/setup.py b/optional_plugins/html/setup.py
    index eb8d584..4ba8675 100644
    --- a/optional_plugins/html/setup.py
    +++ b/optional_plugins/html/setup.py
    @@ -19,7 +19,7 @@ from setuptools import setup, find_packages

     setup(name='avocado_result_html',
           description='Avocado HTML Report for Jobs',
    -      version='47.0',
    +      version='48.0',
           author='Avocado Developers',
           author_email='avocado-devel@redhat.com',
           url='http://avocado-framework.github.io/',
    diff --git a/optional_plugins/robot/setup.py b/optional_plugins/robot/setup.py
    index 1f44b72..700eba0 100644
    --- a/optional_plugins/robot/setup.py
    +++ b/optional_plugins/robot/setup.py
    @@ -19,7 +19,7 @@ from setuptools import setup, find_packages

     setup(name='avocado-robot',
           description='Avocado Plugin for Execution of Robot Framework tests',
    -      version='47.0',
    +      version='48.0',
           author='Avocado Developers',
           author_email='avocado-devel@redhat.com',
           url='http://avocado-framework.github.io/',
    diff --git a/optional_plugins/runner_docker/setup.py b/optional_plugins/runner_docker/setup.py
    index 2d235c8..954c6e7 100644
    --- a/optional_plugins/runner_docker/setup.py
    +++ b/optional_plugins/runner_docker/setup.py
    @@ -19,7 +19,7 @@ from setuptools import setup, find_packages

     setup(name='avocado-runner-docker',
           description='Avocado Runner for Execution on Docker Containers',
    -      version='47.0',
    +      version='48.0',
           author='Avocado Developers',
           author_email='avocado-devel@redhat.com',
           url='http://avocado-framework.github.io/',
    diff --git a/optional_plugins/runner_remote/setup.py b/optional_plugins/runner_remote/setup.py
    index 5fe58dc..5aae9c5 100644
    --- a/optional_plugins/runner_remote/setup.py
    +++ b/optional_plugins/runner_remote/setup.py
    @@ -19,7 +19,7 @@ from setuptools import setup, find_packages

     setup(name='avocado-runner-remote',
           description='Avocado Runner for Remote Execution',
    -      version='47.0',
    +      version='48.0',
           author='Avocado Developers',
           author_email='avocado-devel@redhat.com',
           url='http://avocado-framework.github.io/',
    diff --git a/optional_plugins/runner_vm/setup.py b/optional_plugins/runner_vm/setup.py
    index 168464a..44b56e7 100644
    --- a/optional_plugins/runner_vm/setup.py
    +++ b/optional_plugins/runner_vm/setup.py
    @@ -19,7 +19,7 @@ from setuptools import setup, find_packages

     setup(name='avocado-runner-vm',
           description='Avocado Runner for libvirt VM Execution',
    -      version='47.0',
    +      version='48.0',
           author='Avocado Developers',
           author_email='avocado-devel@redhat.com',
           url='http://avocado-framework.github.io/',

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
