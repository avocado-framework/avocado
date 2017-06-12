========================
 Avocado Test Framework
========================

Avocado is a set of tools and libraries to help with automated testing.

One can call it a test framework with benefits.  Native tests are
written in Python and they follow the unittest
(https://docs.python.org/2.7/library/unittest.html) pattern, but any
executable can serve as a test.

Avocado is composed of:

* A test runner that lets you execute tests. Those tests can be either
  written in your language of choice, or be written in Python and use
  the available libraries. In both cases, you get facilities such as
  automated log and system information collection.

* Libraries that help you write tests in a concise, yet expressive and
  powerful way.  You can find more information about what libraries
  are intended for test writers at:
  http://avocado-framework.readthedocs.io/en/latest/api/utils/avocado.utils.html

* Plugins that can extend and add new functionality to the Avocado
  Framework.  More info at:
  http://avocado-framework.readthedocs.io/en/latest/Plugins.html

Avocado is built on the experience accumulated with Autotest
(http://autotest.github.io), while improving on its weaknesses and
shortcomings.

Installing Avocado
==================

Installing from Packages
------------------------

Fedora
~~~~~~

Avocado is available in stock Fedora 24 and later.  The main package
name is ``python-avocado``, and can be installed with::

    dnf install python-avocado

Other available packages (depending on the Avocado version) may include:

* ``python-avocado-examples``: contains example tests and other example files
* ``python2-avocado-plugins-output-html``: HTML job report plugin
* ``python2-avocado-plugins-resultsdb``: propagate Job results to Resultsdb
* ``python2-avocado-plugins-runner-remote``: execution of jobs on a remote machine
* ``python2-avocado-plugins-runner-vm``: execution of jobs on a libvirt based VM
* ``python2-avocado-plugins-runner-docker``: execution of jobs on a Docker container
* ``python-avocado-plugins-varianter-yaml-to-mux``: parse YAML file into variants

Fedora from Avocado's own Repo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Avocado project also makes the latest release, and the LTS (Long
Term Stability) releases available from its own package repository.
To use it, first get the package repositories configuration file by
running the following command::

    sudo curl https://repos-avocadoproject.rhcloud.com/static/avocado-fedora.repo -o /etc/yum.repos.d/avocado.repo

Now check if you have the ``avocado`` and ``avocado-lts`` repositories configured by running::

    sudo dnf repolist avocado avocado-lts
    ...
    repo id      repo name                          status
    avocado      Avocado                            50
    avocado-lts  Avocado LTS (Long Term Stability)  disabled

Regular users of Avocado will want to use the standard ``avocado``
repository, which tracks the latest Avocado releases.  For more
information about the LTS releases, please refer to the Avocado Long
Term Stability thread
(https://www.redhat.com/archives/avocado-devel/2016-April/msg00038.html)
and to your package management docs on how to switch to the
``avocado-lts`` repo.

Finally, after deciding between regular Avocado releases or LTS, you
can install the RPM packages by running the following commands::

    dnf install python-avocado

Additionally, other Avocado packages are available for Fedora:

* ``python-avocado-examples``: contains example tests and other example files
* ``python2-avocado-plugins-output-html``: HTML job report plugin
* ``python2-avocado-plugins-resultsdb``: propagate Job results to Resultsdb
* ``python2-avocado-plugins-runner-remote``: execution of jobs on a remote machine
* ``python2-avocado-plugins-runner-vm``: execution of jobs on a libvirt based VM
* ``python2-avocado-plugins-runner-docker``: execution of jobs on a Docker container
* ``python-avocado-plugins-varianter-yaml-to-mux``: parse YAML file into variants

Enterprise Linux
~~~~~~~~~~~~~~~~

Avocado packages for Enterprise Linux are available from the Avocado
project RPM repository.  Additionally, some packages from the EPEL repo are
necessary, so you need to enable it first.  For EL7, running the
following command should do it::

    yum install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

Then you must use the Avocado project RHEL repo
(https://repos-avocadoproject.rhcloud.com/static/avocado-el.repo).
Running the following command should give you the basic Avocado
installation ready::

    curl https://repos-avocadoproject.rhcloud.com/static/avocado-el.repo -o /etc/yum.repos.d/avocado.repo
    yum install python-avocado

Other available packages (depending on the Avocado version) may include:

* ``python-avocado-examples``: contains example tests and other example files
* ``python2-avocado-plugins-output-html``: HTML job report plugin
* ``python2-avocado-plugins-runner-remote``: execution of jobs on a remote machine
* ``python2-avocado-plugins-runner-vm``: execution of jobs on a libvirt based VM
* ``python2-avocado-plugins-runner-docker``: execution of jobs on a Docker container

The LTS (Long Term Stability) repositories are also available for
Enterprise Linux.  For more information about the LTS releases, please
refer to
http://avocado-framework.readthedocs.io/en/latest/rfcs/LongTermStability.html
and to your package management docs on how to switch to the
``avocado-lts`` repo.

OpenSUSE
~~~~~~~~

The OpenSUSE project packages LTS versions of Avocado
(https://build.opensuse.org/package/show/Virtualization:Tests/avocado).
You can install packages by running the following commands::

  zypper install avocado

Debian
~~~~~~

DEB package support is available in the source tree (look at the
``contrib/packages/debian`` directory.  No actual packages are
provided by the Avocado project or the Debian repos.


Setting up a Development Environment
====================================

If you want to develop Avocado, or just run it directly from the GIT
repository, fetch the source code and run::

  make develop

From this point on, running ``avocado`` should load everything from
your current source code checkout.

Brief Usage Instructions
========================

To list available tests, call the ``list`` subcommand.  For example::

  avocado list

  INSTRUMENTED <examples_path>/tests/abort.py:AbortTest.test
  INSTRUMENTED <examples_path>/tests/canceltest.py:CancelTest.test
  ...
  SIMPLE       <examples_path>/tests/passtest.sh

To run a test, call the ``run`` command::

  avocado run <examples_path>/tests/passtest.sh
  JOB ID     : <id>
  JOB LOG    : <job-results>/job-<date>-<shortid>/job.log
  (1/1) <examples_path>/tests/passtest.sh: PASS (0.04 s)
  RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
  JOB TIME   : 0.14 s

To continue exploring Avocado, check out the output of ``avocado --help``
and the test runner man-page, accessible via ``man avocado``.

Documentation
=============

Avocado comes with in tree documentation about the most advanced features and
its API. It can be built with ``sphinx``, but a publicly available build of
the latest master branch documentation and releases can be seen on `read the
docs <https://readthedocs.org/>`__:

http://avocado-framework.readthedocs.org/

If you want to build the documentation yourself:

1) Make sure you have the package ``python-sphinx`` installed. For Fedora::

    $ sudo yum install python-sphinx

2) For Mint/Ubuntu/Debian::

    $ sudo apt-get install python-sphinx

3) Optionally, you can install the read the docs theme, that will make your
   in-tree documentation look just like the online version::

    $ sudo pip install sphinx_rtd_theme

4) Build the docs::

    $ make -C docs html

5) Once done, point your browser to::

    $ [your-browser] docs/build/html/index.html

