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

Avocado is primarily written in Python, so a standard Python installation
is possible and often preferable.

.. tip:: If you are looking for Virtualization specific testing, also
         consider looking at `Avocado-VT installation instructions
         <https://avocado-vt.readthedocs.io/en/latest/GetStartedGuide.html#installing-avocado-vt>`_
         after finishing the Avocado installation.

Installing with standard Python tools
-------------------------------------

The simplest installation method is through ``pip``.  On most POSIX
systems with Python 2.7 and ``pip`` available, installation can be
performed with a single command::

  pip install --user avocado-framework

This will fetch the Avocado package (and possibly some of its
dependecies) from the PyPI repository, and will attempt to install it
in the user's home directory (usually under ``~/.local``).

Tip: If you want to perform a system-wide installation, drop the
``--user`` switch.

If you want even more isolation, Avocado can also be installed in a
Python virtual environment. with no additional steps besides creating
and activating the "venv" itself::

  python -m virtualenv /path/to/new/virtual_environment
  . /path/to/new/virtual_environment/bin/activate
  pip install avocado-framework

Please note that this installs the Avocado core functionality.  Many
Avocado features are distributed as non-core plugins, also available
as additional packages on PyPI.  You should be able to find them via
``pip search avocado-framework-plugin | grep
avocado-framework-plugin``. Some of them are listed below:

* ``avocado-framework-plugin-glib``: Execution of GLib Test Framework tests
* ``avocado-framework-plugin-golang``: Execution of Golang tests
* ``avocado-framework-plugin-loader-yaml``: Loads tests from YAML files
* ``avocado-framework-plugin-result-html``: HTML Report for Jobs
* ``avocado-framework-plugin-result-upload``: Propagate Job results to remote host
* ``avocado-framework-plugin-resultsdb``: Propagate Job results to Resultsdb
* ``avocado-framework-plugin-robot``: Execution of Robot Framework tests
* ``avocado-framework-plugin-runner-docker``: Runner for Execution on Docker Containers
* ``avocado-framework-plugin-runner-remote``: Runner for Remote Execution
* ``avocado-framework-plugin-runner-vm``: Runner for libvirt VM Execution
* ``avocado-framework-plugin-varianter-cit``: Varianter with combinatorial capabilities
* ``avocado-framework-plugin-varianter-pict``: Varianter with combinatorial capabilities by PICT
* ``avocado-framework-plugin-varianter-yaml-to-mux``: Parse YAML file into variants

Installing from Packages
------------------------

Fedora
~~~~~~

Avocado is available in stock Fedora 24 and later.  The main package
name is ``python-avocado``, and can be installed with::

    dnf install python-avocado

Other available packages (depending on the Avocado version) may include:

* ``python-avocado-examples``: Avocado Test Framework Example Tests
* ``python2-avocado-plugins-output-html``: Avocado HTML report plugin
* ``python2-avocado-plugins-runner-remote``: Avocado Runner for Remote Execution
* ``python2-avocado-plugins-runner-vm``: Avocado Runner for libvirt VM Execution
* ``python2-avocado-plugins-resultsdb``: Avocado plugin to propagate job results to ResultsDB
* ``python2-avocado-plugins-runner-docker``: Avocado Runner for Execution on Docker Containers
* ``python2-avocado-plugins-varianter-yaml-to-mux``: Avocado plugin to generate variants out of yaml files

Fedora from Avocado's own Repo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Avocado project also makes the latest release, and the LTS (Long
Term Stability) releases available from its own package repository.
To use it, first get the package repositories configuration file by
running the following command::

    sudo curl https://avocado-project.org/data/repos/avocado-fedora.repo -o /etc/yum.repos.d/avocado.repo

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
* ``python2-avocado-plugins-varianter-pict``: varianter with combinatorial capabilities by PICT

Enterprise Linux
~~~~~~~~~~~~~~~~

Avocado packages for Enterprise Linux are available from the Avocado
project RPM repository.  Additionally, some packages from the EPEL repo are
necessary, so you need to enable it first.  For EL7, running the
following command should do it::

    yum install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

Then you must use the Avocado project RHEL repo
(https://avocado-project.org/data/repos/avocado-el.repo).
Running the following command should give you the basic Avocado
installation ready::

    curl https://avocado-project.org/data/repos/avocado-el.repo -o /etc/yum.repos.d/avocado.repo
    yum install python-avocado

Other available packages (depending on the Avocado version) may include:

* ``python-avocado-bash``: Avocado Test Framework Bash Utilities
* ``python-avocado-common``: Avocado common files
* ``python-avocado-examples``: Avocado Test Framework Example Tests
* ``python2-avocado-plugins-glib``: Avocado Plugin for Execution of GLib Test Framework tests
* ``python2-avocado-plugins-golang``: Avocado Plugin for Execution of golang tests
* ``python2-avocado-plugins-loader-yaml``: Avocado Plugin that loads tests from YAML files
* ``python2-avocado-plugins-output-html``: Avocado HTML report plugin
* ``python2-avocado-plugins-result-upload``: Avocado Plugin to propagate Job results to a remote host
* ``python2-avocado-plugins-resultsdb``: Avocado plugin to propagate job results to ResultsDB
* ``python2-avocado-plugins-runner-docker``: Avocado Runner for Execution on Docker Containers
* ``python2-avocado-plugins-runner-remote``: Avocado Runner for Remote Execution
* ``python2-avocado-plugins-runner-vm``: Avocado Runner for libvirt VM Execution
* ``python2-avocado-plugins-varianter-cit``: Varianter with Combinatorial Independent Testing capabilities
* ``python2-avocado-plugins-varianter-pict``: Varianter with combinatorial capabilities by PICT
* ``python2-avocado-plugins-varianter-yaml-to-mux``: Avocado plugin to generate variants out of yaml files

The LTS (Long Term Stability) repositories are also available for
Enterprise Linux.  For more information about the LTS releases, please
refer to
http://avocado-framework.readthedocs.io/en/latest/rfcs/LongTermStability.html
and to your package management docs on how to switch to the
``avocado-lts`` repo.

Latest Development RPM Packages from COPR
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Avocado provides a repository of continuously built packages from the
GitHub repository's master branch.  These packages are currently
available for EL7, Fedora 28 and Fedora 29, for both x86_64 and
ppc64le.

If you're interested in using the very latest development version of
Avocado from RPM packages, you can do so by running::

  dnf copr enable @avocado/avocado-latest
  dnf install python*-avocado*

The following image shows the status of the Avocado packages building
on COPR:

  .. image:: https://copr.fedorainfracloud.org/coprs/g/avocado/avocado-latest/package/python-avocado/status_image/last_build.png
     :target: https://copr.fedorainfracloud.org/coprs/g/avocado/avocado-latest/package/python-avocado/

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

To continue exploring Avocado, check out the output of ``avocado --help``.  When
running Avocado out of package-based installs, its man page should also be
accessible via ``man avocado``.

Documentation
=============

Avocado's latest documentation build can be found at
https://avocado-framework.readthedocs.io/.
