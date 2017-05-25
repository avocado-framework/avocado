===============
Robot Framework
===============

"Robot Framework is a generic test automation framework for acceptance
testing and acceptance test-driven development (ATDD). "
(http://robotframework.org/)

Install
-------

Install `robot` is as simple as::

    ~$ sudo pip install robotframework

For the purpose of this documentation, let's install `python-selenium`
as well::

    ~$ sudo dnf install python-selenium
    ~$ sudo pip install robotframework-selenium2library

Web Testing Demo Package
------------------------

To provide practical examples, let's download the Web Demo package
(please check the correct version)::

    $ cd ~/Downloads
    ~/Downloads$ wget https://bitbucket.org/robotframework/webdemo/downloads/WebDemo-20150901.zip
    ~/Downloads$ unzip WebDemo-20150901.zip
    Archive:  WebDemo-20150901.zip
      inflating: WebDemo/README.rst
      inflating: WebDemo/demoapp/server.py
      inflating: WebDemo/demoapp/html/welcome.html
      inflating: WebDemo/demoapp/html/error.html
      inflating: WebDemo/demoapp/html/index.html
      inflating: WebDemo/demoapp/html/demo.css
      inflating: WebDemo/login_tests/resource.robot
      inflating: WebDemo/login_tests/gherkin_login.robot
      inflating: WebDemo/login_tests/invalid_login.robot
      inflating: WebDemo/login_tests/valid_login.robot

Running Robot Tests with Avocado
--------------------------------

Before testing the Demo Web application, don't forget to start the app
server::

    ~$ python  ~/Downloads/WebDemo/demoapp/server.py &
    [1] 6210 Demo server starting on port 7272.

The standard usage of `robot` would be::

    ~$ robot ~/Downloads/WebDemo/login_tests/

With that in mind, you can easily run the robot tests in Avocado using
the command::

    ~$ avocado run ~/Downloads/WebDemo/login_tests/ --external-runner /usr/bin/robot
    JOB ID     : b31c4a312c8ad984a72370c8ea9762b9444eb073
    JOB LOG    : $HOME/avocado/job-results/job-2017-03-16T16.33-b31c4a3/job.log
     (1/1) $HOME/Downloads/WebDemo/login_tests/: PASS (9.15 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    TESTS TIME : 9.15 s
    JOB HTML   : $HOME/avocado/job-results/job-2017-03-16T16.33-b31c4a3/html/results.html

The inconvenience with the execution above is that all `robot` tests
present in the suite will be executed as only one Avocado test. Of
course you can inspect the Avocado `job.log` to see all tests results,
but if you are expecting more granularity, making each `robot` test to
be a different Avocado test, you might be interested in the contrib
scripts present in Avocado repository.

Contrib Scripts
---------------

Avocado repository contains two contrib scripts to provide a better
integration with `robot`.

- `contrib/scripts/robot-list-tests.py`: This script will receive the
  suite paths as arguments and will create a list of tests to be passed
  for the external runner. We created an arbitrary format containing
  the suite path, the suite name and the test name. Some extra escape
  characters are present to make it work smoothly when used in Avocado.
  You can take a look in this script output with::

    ~$ ./git/avocado/contrib/scripts/robot-list-tests.py ~/Downloads/WebDemo/login_tests/
    "\"$HOME/Downloads/WebDemo/login_tests/:Gherkin Login:Valid Login\""
    "\"$HOME/Downloads/WebDemo/login_tests/:Valid Login:Valid Login\""
    "\"$HOME/Downloads/WebDemo/login_tests/:Invalid Login:Invalid Username\""
    "\"$HOME/Downloads/WebDemo/login_tests/:Invalid Login:Invalid Password\""
    "\"$HOME/Downloads/WebDemo/login_tests/:Invalid Login:Invalid Username And Password\""
    "\"$HOME/Downloads/WebDemo/login_tests/:Invalid Login:Empty Username\""
    "\"$HOME/Downloads/WebDemo/login_tests/:Invalid Login:Empty Password\""
    "\"$HOME/Downloads/WebDemo/login_tests/:Invalid Login:Empty Username And Password\""

- `contrib/scripts/robot-test-runner.py`: Meant to be used as the external
  runner, this script expects as argument one item from the list created by
  the `robot-list-tests.py`. After parsing the argument, this script will
  execute the robot command with the corresponding options that are enough
  to run one test only. You can test this script with::

    ~$ ./git/avocado/contrib/scripts/robot-test-runner.py "~/Downloads/WebDemo/login_tests/:Gherkin Login:Valid Login"
    ==============================================================================
    Login Tests
    ==============================================================================
    Login Tests.Gherkin Login :: A test suite with a single Gherkin style test.
    ==============================================================================
    Valid Login                                                           | PASS |
    ------------------------------------------------------------------------------
    Login Tests.Gherkin Login :: A test suite with a single Gherkin st... | PASS |
    1 critical test, 1 passed, 0 failed
    1 test total, 1 passed, 0 failed
    ==============================================================================
    Login Tests                                                           | PASS |
    1 critical test, 1 passed, 0 failed
    1 test total, 1 passed, 0 failed
    ==============================================================================
    Output:  None
    ~$

Complete Integration
--------------------

Putting all pieces together, running Avocado with the contrib scripts
will produce the following results::

    ~$ eval avocado run \
        $(~/git/avocado/contrib/scripts/robot-list-tests.py ~/Downloads/WebDemo/login_tests/) \
        --external-runner ~/git/avocado/contrib/scripts/robot-test-runner.py
    JOB ID     : 43c6acb09c8d4b57296273ff8828ad6b580239b0
    JOB LOG    : $HOME/avocado/job-results/job-2017-03-16T16.28-43c6acb/job.log
     (1/8) "$HOME/Downloads/WebDemo/login_tests/:Gherkin Login:Valid Login": PASS (2.76 s)
     (2/8) "$HOME/Downloads/WebDemo/login_tests/:Valid Login:Valid Login": PASS (2.74 s)
     (3/8) "$HOME/Downloads/WebDemo/login_tests/:Invalid Login:Invalid Username": PASS (2.81 s)
     (4/8) "$HOME/Downloads/WebDemo/login_tests/:Invalid Login:Invalid Password": PASS (2.81 s)
     (5/8) "$HOME/Downloads/WebDemo/login_tests/:Invalid Login:Invalid Username And Password": PASS (2.78 s)
     (6/8) "$HOME/Downloads/WebDemo/login_tests/:Invalid Login:Empty Username": PASS (2.76 s)
     (7/8) "$HOME/Downloads/WebDemo/login_tests/:Invalid Login:Empty Password": PASS (2.78 s)
     (8/8) "$HOME/Downloads/WebDemo/login_tests/:Invalid Login:Empty Username And Password": PASS (2.75 s)
    RESULTS    : PASS 8 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    TESTS TIME : 22.20 s
    JOB HTML   : $HOME/avocado/job-results/job-2017-03-16T16.28-43c6acb/html/results.html
