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
