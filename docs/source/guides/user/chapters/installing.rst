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
directory (usually under ``~/.local``).

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

Fedora
~~~~~~

Avocado is available in stock Fedora 24 and later.  The main package name is
``python-avocado``, and can be installed with::

    $ dnf install python-avocado

.. _fedora-from-avocados-own-repo:

Fedora from Avocado's own Repo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Avocado project also makes the latest release, and the LTS (Long Term
Stability) releases available from its own package repository.  To use it,
first get the package repositories configuration file by running the following
command::

    $ sudo curl https://avocado-project.org/data/repos/avocado-fedora.repo -o /etc/yum.repos.d/avocado.repo

Now check if you have the ``avocado`` and ``avocado-lts`` repositories
configured by running::

    $ sudo dnf repolist avocado avocado-lts
    ...
    repo id      repo name                          status
    avocado      Avocado                            50
    avocado-lts  Avocado LTS (Long Term Stability)  disabled

Regular users of Avocado will want to use the standard ``avocado`` repository,
which tracks the latest Avocado releases.  For more information about the LTS
releases, please refer to :ref:`rfc-long-term-stability`  and to your package
management docs on how to switch to the ``avocado-lts`` repo.

Finally, after deciding between regular Avocado releases or LTS, you can
install the RPM packages by running the following commands::

    $ dnf install python-avocado


Enterprise Linux
~~~~~~~~~~~~~~~~

Avocado packages for Enterprise Linux are available from the Avocado project
RPM repository.  Additionally, some packages from the EPEL repo are necessary,
so you need to enable it first.  For EL7, running the following command should
do it::

    $ yum install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

Then you must use the Avocado project RHEL repository_.  Running the following
command should give you the basic Avocado installation ready::

    $ curl https://avocado-project.org/data/repos/avocado-el.repo -o /etc/yum.repos.d/avocado.repo
    $ yum install python-avocado

The LTS (Long Term Stability) repositories are also available for Enterprise
Linux.  Please refer to :ref:`rfc-long-term-stability` and to your package
management docs on how to switch to the ``avocado-lts`` repo.

Latest Development RPM Packages from COPR
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Avocado provides a repository of continuously built packages from the GitHub
repository's master branch.  These packages are currently available for EL7,
Fedora 28 and Fedora 29, for both x86_64 and ppc64le.

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
    $ sudo make requirements
    $ sudo python3 setup.py install

.. _repository: https://avocado-project.org/data/repos/avocado-el.repo
.. _OpenSUSE: https://build.opensuse.org/package/show/Virtualization:Tests/avocado
.. _Avocado-VT: https://avocado-vt.readthedocs.io/en/latest/GetStartedGuide.html#installing-avocado-vt
