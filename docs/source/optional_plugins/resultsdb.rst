================
Resultsdb Plugin
================

This optional plugin is intended to propagate the Avocado Job results to
a given resultsdb API URL.

To install the resultsdb plugin from pip, use::

    pip install avocado-framework-plugin-resultsdb

Usage::

    avocado run passtest.py --resultsdb-api http://resultsdb.example.com/api/v2.0/

Optionally, you can provide the URL where the Avocado logs are published::

    avocado run passtest.py --resultsdb-api http://resultsdb.example.com/api/v2.0/ --resultsdb-logs http://avocadologs.example.com/

You can also set the resultsdb API URL and logs URL using a config file::

    [plugins.resultsdb]
    api_url = http://resultsdb.example.com/api/v2.0/
    logs_url = http://avocadologs.example.com/

And then run the Avocado command without the ``--resultsdb-api`` and
``--resultsdb-logs`` options. Notice that the command line options will
have precedence over the configuration file.
