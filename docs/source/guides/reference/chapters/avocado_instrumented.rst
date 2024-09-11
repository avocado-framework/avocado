
The Avocado instrumented lifecycle
==================================

The Avocado instrumented test goes through multiple phases during
its execution. This page describes in detail each of those phases
and overall lifecycle of instrumented test execution.

INIT:
    This is the initialization state of test. Each test is
    created in this state. During the initialization, the test
    attributes are set, environment variables are created, and test
    skip conditions are evaluated.

SETUP:
    The test is in this state when Test.setUp() method is being
    executed.

TEST:
    During this state, the actual test is running.

TEARDOWN:
    During this state, the Test.tearDown() method is being
    executed to make clean up after testing.

FINISHED:
    This state is the end of the test's lifecycle, and the test
    is in this state when the testing and clean up is finished.
    during this phase, the test results are reported to runner and
    the testing is finished.

The whole Test lifecycle is represented by diagram::

                    +--------+
                    |        |
                    |  INIT  +------------+
                    |        |            |
                    +----+---+            |
                         |                |
                         |                |
                     Test|initialized     |
                         |                |
                         |            Test|skipped
                    +----v----+           |
                    |         |           |
                    |  SETUP  +-----------+---+
                    |         |           |   |
                    +----+----+           |   |
                         |                |   |
                         |                |   |
                     Test|set up          |   |
                         |                |   |
                         |                |   |
                    +----v---+            |   |
                    |        |            |   |
        +-----------+  TEST  <------------+   |
        |           |        |                |
        |           +----+---+           Setup|timed out
        |                |                    |
        |     Test finished or timed out      |
        |                |                    |
        |                |                    |
        |         +------v-----+              |
        |         |            |              |
    Test|skipped   |  TEARDOWN  <-------------+
        |         |            |
        |         +------+-----+
        |                |
        |                |
        | Teardown finished or timed out
        |                |
        |                |
        |         +------v-----+
        |         |            |
        +--------->  FINISHED  |
                  |            |
                  +------------+

Timeouts
~~~~~~~~

The avocado instrumented tests can be affected by three types of
timeouts. Test timeout, Task timeout and Job timeout. All of these
timeouts behaves the same from the point of view of Test’s lifecycle,
but the lifecycle will change base on in which state the timeout was
reached. Here is a description of different Test’s lifecycles based
on the interruptions:

Timeout in SETUP
    INIT -> SETUP(interrupted) -> TEARDOWN -> FINISHED (ERROR)

Timeout in TEST
    INIT -> SETUP -> TEST(interrupted) -> TEARDOWN -> FINISHED (INTERRUPTED)

Timeout in TEARDOWN
    INIT -> SETUP -> TEST -> TEARDOWN(interrupted) -> FINISHED (ERROR)

.. note:: If either the Task or Job timeout is reached after some other
    interruption (test or task timeouts) the test is killed in
    the phase where it is (probably TEARDOWN), and it won’t properly
    finish.
