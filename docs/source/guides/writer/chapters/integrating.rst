Integrating Avocado
===================

Coverage.py
~~~~~~~~~~~

Testing software is important, but knowing the effectiveness of the tests,
like which parts are being exercised by the tests, may help develop new tests.

`Coverage.py`_ is a tool designed for measuring code coverage of Python
programs. It runs monitoring the program's source, taking notes of which
parts of the code have been executed. It is possible to use Coverage.py while
running Avocado Instrumented tests or Python unittests.

To make the Coverage.py parameters visible to other processes spawned by
Avocado, create the ``.coveragerc`` file in the project's root folder and set
``source`` parameter to your system under test.
Following is an example::

    [run]
    source = foo/bar

With the ``.coveragerc`` file set, one possible workflow to use Coverage.py to
measure Avocado tests is::

    coverage run -m avocado run tests/foo
    coverage combine
    coverage report

The first command uses Coverage.py to measure the code coverage of the
Avocado tests. Then, `coverage combine` combines all measurement files to a
single ``.coverage`` data file. The `coverage report` shows the report of the
coverage measurement.

For other options related to `Coverage.py`_, visit the software documentation.

.. note:: Currently coverage support is limited working only with
   `ProcessSpawner` (the default spawner) and Coverage.py>=7.5.

.. _Coverage.py: https://coverage.readthedocs.io/
