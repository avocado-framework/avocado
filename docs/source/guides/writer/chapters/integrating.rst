Integrating Avocado
===================

Coverage.py
~~~~~~~~~~~

Testing software is important, but knowing the effectiveness of the tests,
like which parts are being exercised by the tests, may help develop new tests.

`Coverage.py`_ is a tool designed for measuring code coverage of Python
programs. It runs monitoring the program's source, taking notes of which
parts of the code have been executed.

It is possible to use Coverage.py while running Avocado Instrumented tests.
As Avocado spawn sub-processes to run the tests, the `concurrency` parameter
should be set to `multiprocessing`.

To make the Coverage.py parameters visible to other processes spawned by
Avocado, create the ``.coveragerc`` file in the project's root folder.
Following is an example::

    [run]
    concurrency = multiprocessing
    source = foo/bar
    parallel = true

According to the documentation of Coverage.py, when measuring coverage in
a multi-process program, setting the `parallel` parameter will keep the data
separate during the measurement.

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

.. _Coverage.py: https://coverage.readthedocs.io/
