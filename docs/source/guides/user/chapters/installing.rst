.. _installing:

Installing
==========

Avocado is primarily written in Python, so a standard Python installation is
possible and often preferable. You can also install from your Linux distribution
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
with Python 3.8 (or later) and ``pip`` available, installation can be performed
with a single command::

  $ pip3 install --user avocado-framework

This will fetch the Avocado package (and possibly some of its dependencies) from
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


.. _installing-from-packages:

Installing from packages
------------------------

.. _fedora-from-avocados-own-repo:

Fedora
~~~~~~

Avocado is available as a standard Fedora package.  Simply run::

  $ dnf install python3-avocado

The exact version of Avocado is dependent on the Fedora version and
its release constraints.  If you're looking to have the latest Avocado
release, please use Avocado's COPR repo, by running::

  $ dnf copr enable @avocado/avocado-latest-release
  $ dnf install python3-avocado

Enterprise Linux
~~~~~~~~~~~~~~~~

The latest release of Avocado is available on the same COPR repo
described previously.  To install the latest Avocado release on
Enterprise Linux 9, run::

  $ dnf copr enable @avocado/avocado-latest-release
  $ dnf install python3-avocado

Latest Development RPM Packages from COPR
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Avocado provides a repository of continuously built packages from the
GitHub repository's master branch.  These packages are currently
available for some of the latest Enterprise Linux and Fedora versions,
for a few different architectures.

If you're interested in using the very latest development version of Avocado
from RPM packages, you can do so by running::

  $ dnf copr enable @avocado/avocado-latest
  $ dnf install python3-avocado*

The following image shows the status of the Avocado packages building on COPR:

  .. image:: https://copr.fedorainfracloud.org/coprs/g/avocado/avocado-latest/package/python-avocado/status_image/last_build.png
     :target: https://copr.fedorainfracloud.org/coprs/g/avocado/avocado-latest/package/python-avocado/

OpenSUSE
~~~~~~~~

The OpenSUSE project provides packages for Avocado. Check the
`Virtualization:Tests project in OpenSUSE build service`_
to get the packages from there.


Debian
~~~~~~

DEB package support is available in the source tree (look at the
``contrib/packages/debian`` directory.  No actual packages are provided by the
Avocado project or the Debian repos.

Installing from source code
---------------------------

First make sure you have a basic set of packages installed. The following
applies to Fedora based distributions, please adapt to your platform::

    $ sudo dnf install -y python3 git gcc python3-pip

Then to install Avocado from the git repository run::

    $ git clone git://github.com/avocado-framework/avocado.git
    $ cd avocado
    $ pip install . --user

To install an optional plugin run::

    $ pip install optional_plugins/<plugin_name> --user

I.e. for the HTML plugin::

    $ pip install optional_plugins/html --user

Check the directory ``optional_plugins`` for additional features you might be
interested in.

.. _Virtualization:Tests project in OpenSUSE build service: https://build.opensuse.org/project/show/Virtualization:Tests
.. _Avocado-VT: https://avocado-vt.readthedocs.io/en/latest/GetStartedGuide.html#installing-avocado-vt
