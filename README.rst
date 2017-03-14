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

Using avocado
-------------

The most straightforward way of `using` avocado is to install packages
available for your distro:

1) Fedora/RHEL

   Avocado is not yet officially packed in Fedora/RHEL, but you can use avocado
   yum repositories by putting corresponding file into ``/etc/yum.repos.d``.

   *  `Fedora repo <https://repos-avocadoproject.rhcloud.com/static/avocado-fedora.repo>`__
   *  `RHEL repo <https://repos-avocadoproject.rhcloud.com/static/avocado-el.repo>`__

   and install it by ``yum install avocado`` (or using ``dnf``)

Once you install it, you can start exploring it by checking the output of
``avocado --help`` and the test runner man-page, accessible via ``man avocado``.

If you want to `develop` avocado, or run it directly from the git repository,
you have a couple of options:

1) The avocado test runner was designed to run in tree, for rapid development
   prototypes. After running::

    $ make develop

   Just use::

    $ scripts/avocado --help

2) Installing avocado in the system is also an option, although remember that
   distutils has no ``uninstall`` functionality::

    $ sudo python setup.py install
    $ avocado --help

Documentation
-------------

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

