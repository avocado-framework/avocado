Mail results Plugin
===================

The Mail result plugin enables you to receive email notifications
for job start and completion events within the Avocado testing framework.

.. note:: Currently only supports Gmail.

Installation
------------

To install the Mail results plugin from pip, use:

.. code-block:: bash

   $ pip install avocado-framework-plugin-result-mail

Configuration
-------------

To use the Mail Result plugin, you need to configure it
in the Avocado settings file.

(`avocado.conf` located /etc/avocado/ if not present you can create the file)
Below is an configuration example:

.. note:: More information on configuration here.
   For detailed configuration instructions,
   please visit `Avocado Configuration <https://red.ht/avocadoconfig>`_.


.. code-block:: ini

   [plugins.mail]

   # The email address to which job notification emails will be sent.
   recipient = avocado@local.com

   # The subject header for the job notification emails.
   header = [AVOCADO JOB NOTIFICATION]

   # The email address from which the job notification emails will be sent.
   sender = avocado@local.com

   # The SMTP server address for sending the emails.
   server = smtp.gmail.com

   # The SMTP server port for sending the emails.
   port = 587

   # The application-specific password for the sender email address.
   password = abcd efgh ijkl mnop

   # The detail level of the email content.
   # Set to false for a summary with essential details
   # or true for detailed information about each failed test.
   verbose = false

Usage
-----

Once configured, the Mail result plugin will automatically
send email notifications for job start and completion events
based on the specified settings.

Obtaining an App Password for Gmail
-----------------------------------

Please follow these steps to generate an App Password:

Create & use app passwords

Important: To create an app password,
you need 2-Step Verification on your Google Account.

#. Go to your Google Account.
#. Select Security.
#. Under "How you sign in to Google," select 2-Step Verification.
#. At the bottom of the page, select App passwords.
#. Enter a name that helps you remember where you’ll use the app password.
#. Select Generate.
#. To enter the app password, follow the instructions on your screen.
#. The app password is the 16-character code that generates on your device.
#. Select Done.

Enter the App Password inside of the avocado configuration file.

Remember to keep this App Password secure and don't share it with anyone.
If you suspect it has been compromised,
you can always revoke it and generate a new one.

Example Plugin Outputs
----------------------

.. code-block:: none

    Verbose True

    Job Notification - Job abca44fb69558024b0af74a5654ab282f00f1253
    ===============================================================

    Job Total Time: 24.03 Seconds
    Job Finished At: 2024-06-25 16:31:58

    Results
    -------

    - PASS: 6
    - ERROR: 0
    - FAIL: 1
    - SKIP: 0
    - WARN: 0
    - INTERRUPT: 0
    - CANCEL: 0

    Test Summary
    ------------

    Name: selftests/safeloader.sh
    Status: FAIL
    Fail Reason: 
    Actual Time Start: 1719325898.06546
    Actual Time End: 1719325902.474006
    ID: static-checks-4-selftests/safeloader.sh
    Log Directory: /home/hlynden/avocado/job-results/job-2024-06-25T16.31-abca44f/test-results/static-checks-4-selftests_safeloader.sh
    Log File: /home/hlynden/avocado/job-results/job-2024-06-25T16.31-abca44f/test-results/static-checks-4-selftests_safeloader.sh/debug.log
    Time Elapsed: 4.410571283999161 seconds
    Time Start: 22630.607959844
    Time End: 22635.018531128
    Tags: {}
    Whiteboard: 



.. code-block:: none

    Verbose False

    Job Notification - Job 83da84014a9cbe7a89bea398eb1608dc04743897
    ===============================================================

    Job Total Time: 24.03 Seconds
    Job Finished At: 2024-06-25 16:31:58

    Results
    -------

    - PASS: 6
    - ERROR: 0
    - FAIL: 1
    - SKIP: 0
    - WARN: 0
    - INTERRUPT: 0
    - CANCEL: 0

    Test Summary
    ------------

    Name: selftests/safeloader.sh
    Fail Reason: 
