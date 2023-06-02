.. _golang-plugin:

=============
Golang Plugin
=============

This optional plugin enables Avocado to list and run tests written using
the `Go programming language`_.

.. _Go programming language: https://golang.org/

To install the Golang plugin from pip, use::

    $ sudo pip install avocado-framework-plugin-golang

If you're running Fedora, you can install the package ``golang-tests`` and run any of the tests
included there. You can try running the ``math`` or ``bufio`` tests like this::

    $ GOPATH=/usr/lib/golang avocado list math
    golang math:TestNaN
    golang math:TestAcos
    golang math:TestAcosh
    golang math:TestAsin
    ... skip ...

And::

    $ GOPATH=/usr/lib/golang avocado run math
    JOB ID     : 9453e09dc5a035e465de6abd570947909d6be228
    JOB LOG    : $HOME/avocado/job-results/job-2021-10-01T13.11-9453e09/job.log
     (001/417) math:TestNaN: STARTED
     (002/417) math:TestAcos: STARTED
     (001/417) math:TestNaN: PASS (0.50 s)
     (002/417) math:TestAcos: PASS (0.51 s)
     (003/417) math:TestAcosh: STARTED
     (004/417) math:TestAsin: STARTED
     (003/417) math:TestAcosh: PASS (0.50 s)
     (004/417) math:TestAsin: PASS (0.51 s)
     (005/417) math:TestAsinh: STARTED
     (006/417) math:TestAtan: STARTED
    ^C
    RESULTS    : PASS 4 | ERROR 0 | FAIL 0 | SKIP 413 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB HTML   : $HOME/avocado/job-results/job-2021-10-01T13.11-9453e09/results.html
    JOB TIME   : 2.76 s

Another option is to try the countavocados examples provided with avocado.
Please fetch the avocado code where this example is included. ::

    $ git clone https://github.com/avocado-framework/avocado.git

Also, disable the `Module-aware mode`_, this can be done with the GO111MODULE environment variable::

    $ go env -w GO111MODULE=off

.. _Module-aware mode: https://golang.org/ref/mod#mod-commands

Then you can ``list`` and ``run`` the countavocados tests provided with the plugin::

    $ GOPATH=$PWD/avocado/optional_plugins/golang/tests  avocado -V list countavocados
    Type   Test                              Tag(s)
    golang countavocados:TestEmptyContainers
    golang countavocados:TestNoContainers
    golang countavocados:ExampleContainers

    Resolver             Reference     Info
    avocado-instrumented countavocados File "countavocados" does not end with ".py"
    exec-test            countavocados File "countavocados" does not exist or is not a executable file

    TEST TYPES SUMMARY
    ==================
    golang: 3

And ::

    $ GOPATH=$PWD/avocado/optional_plugins/golang/tests  avocado run countavocados
    JOB ID     : c4284429a1ff97cd737b6e6fe1c5a83f91007317
    JOB LOG    : $HOME/avocado/job-results/job-2021-10-01T13.35-c428442/job.log
    (1/3) countavocados:TestEmptyContainers: STARTED
    (2/3) countavocados:TestNoContainers: STARTED
    (1/3) countavocados:TestEmptyContainers: PASS (0.50 s)
    (2/3) countavocados:TestNoContainers: PASS (0.50 s)
    (3/3) countavocados:ExampleContainers: STARTED
    (3/3) countavocados:ExampleContainers: PASS (0.50 s)
   RESULTS    : PASS 3 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
   JOB HTML   : $HOME/avocado/job-results/job-2021-10-01T13.35-c428442/results.html
   JOB TIME   : 2.12 s
