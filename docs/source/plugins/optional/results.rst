.. _result-plugins:

==============
Result plugins
==============

Optional plugins providing various types of job results.


HTML results Plugin
===================

This optional plugin creates beautiful human readable results.

To install the HTML plugin from pip, use::

    pip install avocado-framework-plugin-result-html

Once installed it produces the results in job results dir::

    $ avocado run sleeptest.py failtest.py synctest.py
    ...
    JOB HTML  : $HOME/avocado/job-results/job-2014-08-12T15.57-5ffe4792/html/results.html
    ...


This can be disabled via --disable-html-job-result. One can also specify a
custom location via --html . Last but not least --open-browser can be used to
start browser automatically once the job finishes.

.. _results-upload-plugin:

Results Upload Plugin
=====================

This optional plugin is intended to upload the Avocado Job results to
a dedicated sever.

To install the Result Upload plugin from pip, use::

    pip install avocado-framework-plugin-result-upload

Usage::

    avocado run passtest.py --result-upload-url www@avocadologs.example.com:/var/www/html

Avocado logs will be available at following URL:

- ssh ::

    www@avocadologs.example.com:/var/www/html/job-2017-04-21T12.54-1cefe11

- html (If web server is enabled) ::

    http://avocadologs.example.com/job-2017-04-21T12.54-1cefe11/

Such links may be refered by other plugins, such as the ResultsDB plugin

By default upload will be handled by following command ::

    rsync -arz -e 'ssh -o LogLevel=error -o stricthostkeychecking=no -o userknownhostsfile=/dev/null -o batchmode=yes -o passwordauthentication=no'

Optionally, you can customize uploader command, for example following command upload logs to Google storage: ::

    avocado run passtest.py --result-upload-url='gs://avocadolog' --result-upload-cmd='gsutil -m cp -r'

You can also set the ResultUpload URL and command using a config file::

    [plugins.result_upload]
    url = www@avocadologs.example.com:/var/www/htmlavocado/job-results
    command='rsync -arzq'

And then run the Avocado command without the explicit cmd options. Notice
that the command line options will have precedence over the
configuration file.

ResultsDB Plugin
================

This optional plugin is intended to propagate the Avocado Job results to
a given ResultsDB API URL.

To install the ResultsDB plugin from pip, use::

    pip install avocado-framework-plugin-resultsdb

Usage::

    avocado run passtest.py --resultsdb-api http://resultsdb.example.com/api/v2.0/

Optionally, you can provide the URL where the Avocado logs are published::

    avocado run passtest.py --resultsdb-api http://resultsdb.example.com/api/v2.0/ --resultsdb-logs http://avocadologs.example.com/

The --resultsdb-logs is a convenience option that will create links
to the logs in the ResultsDB records. The links will then have the
following formats:

- ResultDB group (Avocado Job)::

    http://avocadologs.example.com/job-2017-04-21T12.54-1cefe11/

- ResultDB result (Avocado Test)::

    http://avocadologs.example.com/job-2017-04-21T12.54-1cefe11/test-results/1-passtest.py:PassTest.test/

You can also set the ResultsDB API URL and logs URL using a config file::

    [plugins.resultsdb]
    api_url = http://resultsdb.example.com/api/v2.0/
    logs_url = http://avocadologs.example.com/

And then run the Avocado command without the --resultsdb-api and
--resultsdb-logs options. Notice that the command line options will
have precedence over the configuration file.
