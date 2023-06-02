ResultsDB Plugin
================

This optional plugin is intended to propagate the Avocado Job results to
a given ResultsDB API URL.

To install the ResultsDB plugin from pip, use::

    pip install avocado-framework-plugin-resultsdb

Usage::

    $ avocado run avocado/examples/tests/passtest.py --resultsdb-api http://resultsdb.example.com/api/v2.0/

Optionally, you can provide the URL where the Avocado logs are published::

    $ avocado run avocado/examples/tests/passtest.py --resultsdb-api http://resultsdb.example.com/api/v2.0/ --resultsdb-logs http://avocadologs.example.com/

The ``--resultsdb-logs`` is a convenience option that will create links
to the logs in the ResultsDB records. The links will then have the
following formats:

- ResultDB group (Avocado Job)::

    http://avocadologs.example.com/job-2021-09-30T22.16-f40403c/

- ResultDB result (Avocado Test)::

    http://avocadologs.example.com/job-2021-09-30T22.16-f40403c/test-results/1-passtest.py:PassTest.test/

You can also set the ResultsDB API URL and logs URL using a config file::

    [plugins.resultsdb]
    api_url = http://resultsdb.example.com/api/v2.0/
    logs_url = http://avocadologs.example.com/

And then run the Avocado command without the ``--resultsdb-api`` and
``--resultsdb-logs`` options. Notice that the command line options will
have precedence over the configuration file.
