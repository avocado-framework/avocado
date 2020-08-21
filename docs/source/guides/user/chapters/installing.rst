.. _installing:

Installing
==========

Avocado is primarily written in Python, so a standard Python installation is
possible and often preferable. You can also install from your distro
repository, if available.

.. note:: Please note that this installs the Avocado core functionality.  Many
        Avocado features are distributed as non-core plugins. Visit the Avocado
        Plugin section on the left menu.

.. tip:: If you are looking for Virtualization specific testing, also consider
         looking at Avocado-VT_ installation instructions after finishing the
         Avocado installation.

Installing from PyPI
--------------------

The simplest installation method is through ``pip``.  On most POSIX systems
with Python 3.4 (or later) and ``pip`` available, installation can be performed
with a single command::

  $ pip3 install --user avocado-framework

This will fetch the Avocado package (and possibly some of its dependecies) from
the PyPI repository, and will attempt to install it in the user's home
directory (usually under ``~/.local``), which you might want to add to your
``PATH`` variable if not done already.

.. tip:: If you want to perform a system-wide installation, drop the ``--user``
  switch.

If you want even more isolation, Avocado can also be installed in a Python
virtual environment. with no additional steps besides creating and activating
the "venv" itself::

  $ python3 -m venv /path/to/new/virtual_environment
  $ source /path/to/new/virtual_environment/bin/activate
  $ pip3 install avocado-framework


Installing from packages
------------------------

.. _fedora-from-avocados-own-repo:

Fedora
~~~~~~

Avocado modules are available on standard Fedora repos starting with
version 29.  To subscribe to the latest version stream, run::

  $ dnf module enable avocado:latest

Or, to use the LTS (Long Term Stability) version stream, run::

  $ dnf module enable avocado:69lts

Then proceed to install a module profile or individual packages.  If you're
unsure about what to do, simply run::

  $ dnf module install avocado

Enterprise Linux
~~~~~~~~~~~~~~~~

Avocado modules are also available on EPEL (Extra Packages for Enterprise Linux)
repos, starting with version 8.  To enable the EPEL repository, run::

  $ dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm

Then to enable the module, run::

  $ dnf module enable avocado:latest

And finally, install any number of packages, such as::

  $ dnf install python3-avocado python3-avocado-plugins-output-html python3-avocado-plugins-varianter-yaml-to-mux

Latest Development RPM Packages from COPR
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Avocado provides a repository of continuously built packages from the
GitHub repository's master branch.  These packages are currently
available for some of the latest Enterprise Linux and Fedora versions,
for a few different architectures.

If you're interested in using the very latest development version of Avocado
from RPM packages, you can do so by running::

  $ dnf copr enable @avocado/avocado-latest
  $ dnf install python*-avocado*

The following image shows the status of the Avocado packages building on COPR:

  .. image:: https://copr.fedorainfracloud.org/coprs/g/avocado/avocado-latest/package/python-avocado/status_image/last_build.png
     :target: https://copr.fedorainfracloud.org/coprs/g/avocado/avocado-latest/package/python-avocado/

OpenSUSE
~~~~~~~~

The `OpenSUSE`_ project packages LTS versions of Avocado.  You can install
packages by running the following commands::

  $ sudo zypper install avocado

Debian
~~~~~~

DEB package support is available in the source tree (look at the
``contrib/packages/debian`` directory.  No actual packages are provided by the
Avocado project or the Debian repos.

Installing from source code
---------------------------

First make sure you have a basic set of packages installed. The following
applies to Fedora based distributions, please adapt to your platform::

    $ sudo dnf install -y python3 git gcc python3-devel python3-pip libvirt-devel libffi-devel openssl-devel libyaml-devel redhat-rpm-config xz-devel

Then to install Avocado from the git repository run::

    $ git clone git://github.com/avocado-framework/avocado.git
    $ cd avocado
    $ sudo python3 setup.py install

.. _OpenSUSE: https://build.opensuse.org/package/show/Virtualization:Tests/avocado
.. _Avocado-VT: https://avocado-vt.readthedocs.io/en/latest/GetStartedGuide.html#installing-avocado-vt
