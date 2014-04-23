Avocado Test Framework
======================

Avocado is an experimental test framework that is built on the experience
accumulated with `autotest <http://autotest.github.io/>`__.
It aims to implement the good concepts that make autotest a good test
framework:

* Extensive test API.
* Rich logging and system info collecting facilities all executed transparently.
* Loosely coupled components that can help to fully automate testing on a grid
  of test machines.

While trying to streamline it and make it easier, more approachable for the
single developer looking to improve testing for his/her project.

Using avocado
-------------

The most recommended way of `using` avocado is to install packages available
for your distro. Check the Documentation section for links to package repos
and install instructions.

If you want to `develop` avocado, you have some options:

1) The avocado test runner was designed to run in tree, for rapid development
   prototypes. Just use::

    $ scripts/avocado --help

2) Installing avocado in the system is also an option, although remember that
   distutils has no ``uninstall`` functionality::

    $ sudo python setup.py install
    $ avocado --help

Documentation
-------------

Avocado comes with in tree documentation, that can be built with ``sphinx``.
A publicly available build of the latest master branch documentation and
releases can be seen on `read the docs <https://readthedocs.org/>`__:

http://avocado-framework.readthedocs.org/

If you want to build the documentation, here are the instructions:

1) Make sure you have the package ``python-sphinx`` installed. For Fedora::

    $ sudo yum install python-sphinx

2) For Ubuntu/Debian::

    $ sudo apt-get install python-sphinx

3) Optionally, you can install the read the docs theme, that will make your
   in-tree documentation to look just like in the online version::

    $ sudo pip install sphinx_rtd_theme

4) Build the docs::

    $ make -C docs html

5) Once done, point your browser to::

    $ [your-browser] docs/build/html/index.html

