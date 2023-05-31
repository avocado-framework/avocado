.. _result-plugins:

==============
Result plugins
==============

Optional plugins providing various types of job results.

If you want to run the examples provided below, please fetch the avocado code
where these examples are included. ::

    $ git clone https://github.com/avocado-framework/avocado.git


.. toctree::
   :maxdepth: 2

   html

.. _results-upload-plugin:

Results Upload Plugin
=====================

This optional plugin is intended to upload the Avocado Job results to
a dedicated sever.

To install the Result Upload plugin from pip, use::

    pip install avocado-framework-plugin-result-upload

Usage::

    $ avocado run avocado/examples/tests/passtest.py --result-upload-url www@avocadologs.example.com:/var/www/html
    JOB ID     : f40403c7409ef998f293a7c83ee456c32cb6547a
    JOB LOG    : $HOME/avocado/job-results/job-2021-09-30T22.16-f40403c/job.log
     (1/1) avocado/examples/tests/passtest.py:PassTest.test: STARTED
     (1/1) avocado/examples/tests/passtest.py:PassTest.test: PASS (0.01 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB HTML   : $HOME/avocado/job-results/job-2021-09-30T22.16-f40403c/results.html


Avocado logs will be available at following URL:

- ssh

    www@avocadologs.example.com:/var/www/html/job-2021-09-30T22.16-f40403c

- html (If web server is enabled)

    http://avocadologs.example.com/job-2021-09-30T22.16-f40403c/

Such links may be referred by other plugins, such as the ResultsDB plugin.

By default upload will be handled by following command ::

    rsync -arz -e 'ssh -o LogLevel=error -o stricthostkeychecking=no -o userknownhostsfile=/dev/null -o batchmode=yes -o passwordauthentication=no'

Optionally, you can customize uploader command, for example following command upload logs to Google storage: ::

    $ avocado run avocado/examples/tests/passtest.py --result-upload-url='gs://avocadolog' --result-upload-cmd='gsutil -m cp -r'

You can also set the ResultUpload URL and command using a config file::

    [plugins.result_upload]
    url = www@avocadologs.example.com:/var/www/htmlavocado/job-results
    command='rsync -arzq'

And then run the Avocado command without the explicit command options. Notice
that the command line options will have precedence over the configuration file.

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
