.. _avocado-classless-plugin:

==================================
Avocado-Classless Test Type Plugin
==================================

This optional plugin enables the usage of simpler tests, that do not
require an Avocado Test class, that is, it does not require test writers
to follow the JUnit, AKA unittest, pattern.

To install the Robot plugin from pip, use::

    $ sudo pip install avocado-framework-plugin-avocado-classless

After installed, you can list/run Robot tests the same way you do with
other types of tests.

For example, use the test included in the avocado code ::

    $ git clone https://github.com/avocado-framework/avocado.git

To list the tests, execute::

    $ avocado list avocado/optional_plugins/avocado_classless/tests/example.py

Directories are also accepted. To run the tests, execute::

    $ avocado run avocado/optional_plugins/avocado_classless/tests/example.py
