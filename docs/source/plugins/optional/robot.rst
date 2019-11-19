============
Robot Plugin
============

This optional plugin enables Avocado to work with tests originally
written using the `Robot Framework <http://robotframework.org/>`_ API.

To install the Robot plugin from pip, use::

    $ sudo pip install avocado-framework-plugin-robot

After installed, you can list/run Robot tests the same way you do with
other types of tests.

To list the tests, execute::

    $ avocado list ~/path/to/robot/tests/test.robot

Directories are also accepted. To run the tests, execute::

    $ avocado run ~/path/to/robot/tests/test.robot
