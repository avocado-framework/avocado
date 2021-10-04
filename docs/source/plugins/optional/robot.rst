.. _robot-plugin:

============
Robot Plugin
============

This optional plugin enables Avocado to work with tests originally
written using the `Robot Framework <http://robotframework.org/>`_ API.

To install the Robot plugin from pip, use::

    $ sudo pip install avocado-framework-plugin-robot

After installed, you can list/run Robot tests the same way you do with
other types of tests.

For example, use the test included in the avocado code ::

    $ git clone https://github.com/avocado-framework/avocado.git

To list the tests, execute::

    $ avocado list avocado/optional_plugins/robot/tests/avocado.robot
    robot $HOME/avocado/optional_plugins/robot/tests/avocado.robot:Avocado.NoSleep
    robot $HOME/avocado/optional_plugins/robot/tests/avocado.robot:Avocado.Sleep

Directories are also accepted. To run the tests, execute::

    $ avocado run avocado/optional_plugins/robot/tests/avocado.robot
    JOB ID     : 1501f546890024f2af8e26ab49ba511154bebab9
    JOB LOG    : $HOME/avocado/job-results/job-2021-09-30T21.48-1501f54/job.log
     (2/2) $HOME/avocado/optional_plugins/robot/tests/avocado.robot:Avocado.Sleep: STARTED
     (1/2) $HOME/avocado/optional_plugins/robot/tests/avocado.robot:Avocado.NoSleep: STARTED
     (1/2) $HOME/avocado/optional_plugins/robot/tests/avocado.robot:Avocado.NoSleep: PASS (0.06 s)
     (2/2) $HOME/avocado/optional_plugins/robot/tests/avocado.robot:Avocado.Sleep: PASS (0.07 s)
    RESULTS    : PASS 2 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB HTML   : $HOME/avocado/job-results/job-2021-09-30T21.48-1501f54/results.html
    JOB TIME   : 0.99 s
