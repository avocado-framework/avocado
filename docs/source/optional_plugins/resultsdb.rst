================
Resultsdb Plugin
================

This optional plugin is intended to propagate the Avocado Job results to
a given resultsdb API URL.

To install the resultsdb plugin from pip, use::

    pip install avocado-framework-plugin-resultsdb

Usage::

    avocado run passtest.py --resultsdb-api http://resultsdb.example.com/api/v2.0/

You can also set the resultsdb API URL in the ``avocado.conf`` file::

    [optional.plugins]
    resultsdb_api = http://resultsdb.example.com/api/v2.0/

And then run the Avocado command without the ``--resultsdb-api`` option.
