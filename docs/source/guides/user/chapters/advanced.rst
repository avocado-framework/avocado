Advanced usage
==============

Custom Runnable Identifier
--------------------------

In some cases, you might have a wrapper as an entry point for the tests, so
Avocado will use only the wrapper as test id. For instance, imagine a Makefile
with some targets ('foo', 'bar') and each target is one test. Having a single
test suite with a test calling `foo`, it will make Avocado print something like
this:


```
JOB ID     : b6e5bdf2c891382bbde7f24e906a168af351154a
JOB LOG    : ~/avocado/job-results/job-2021-09-24T17.39-b6e5bdf/job.log
 (1/1) make: STARTED
 (1/1) make: PASS (2.72 s)
RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
JOB HTML   : ~/avocado/job-results/job-2021-09-24T17.39-b6e5bdf/results.html
JOB TIME   : 5.49 s
```

This is happening because Avocado is using the 'uri' as identifier with in the
current Runnables.

You can change that by setting a custom format with the option
`runner.identifier_format` in you `avocado.conf` file. For instance:

```
[runner]
identifier_format = "{uri}-{args[0]}"
```

With the above adjustment, running the same suite it will produce something
like this:

```
JOB ID     : 577b70b079e9a6f325ff3e73fd9b93f80ee7f221
JOB LOG    : /home/local/avocado/job-results/job-2021-11-23T13.12-577b70b/job.log
 (1/1) "/usr/bin/make-foo": STARTED
 (1/1) "/usr/bin/make-foo": PASS (0.01 s)
RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
JOB HTML   : ~/avocado/job-results/job-2021-11-23T13.12-577b70b/results.html
JOB TIME   : 0.97 s
```

For the `identifier_format` you can use any f-string that it will use `{uri}`,
`{args}` or `{kwargs}`. By default it will use `{uri}`.

When using args, since it is a list, you can use in two different ways:
"{args}" for the entire list, or "{args[n]}" for a specific element inside this
list.  The same is valid when using "{kwargs}". With kwargs, since it is a
dictionary, you have to specify a key as index and then the values are used.

For instance if you have a kwargs value named 'DEBUG', a valid usage could be:
"{kwargs[DEBUG]}" and this will print the current value to this variable (i.e:
True or False).


.. note:: Please, keep in mind this is an experimental feature, and for now you
   have to use it in combination with :ref:`documentation<the_hint_files>`.

.. note:: Also, be aware this feature it is meant to set custom Runnable
   identifiers strings only.

Test Runner Selection
---------------------

To effectively run a job with tests, Avocado makes use of a well
described and pluggable interface.  This means that users can choose
(and developers can write) their own runners.

Runner choices can be seen by running ``avocado plugins``::

  ...
  Plugins that run test suites on a job (suite.runner):
  nrunner nrunner based implementation of job compliant runner

And to select a different test runner (if another one exists)::

  avocado run --suite-runner=other_runner_plugin ...

Running tests with an external runner
-------------------------------------

It's pretty standard to have organically grown test suites in most software
projects, and these usually include a custom-built, specific test runner who
knows how to find and run their tests.

Still, running those tests inside Avocado may be a good idea for various
reasons, including having results in different human and machine-readable
formats and collecting system information alongside those tests (the Avocado's
Sysinfo functionality), and more.

Avocado makes that possible using its "external runner" feature. The most basic
way of using it is::


  $ avocado-external-runner external_runner foo bar baz


In this example, Avocado will report individual test results for tests foo,
bar, and baz. The actual results will be based on the return code of individual
executions of /path/to/external_runner foo, /path/to/external_runner bar and
finally /path/to/external_runner baz.

As another way to explain how this feature works, think of the "external
runner" as an interpreter. The individual tests as anything that this
interpreter recognizes and can execute. A UNIX shell, say /bin/sh could be
considered an external runner, and files with shellcode could be viewed as
tests::


  $ echo "exit 1" > /tmp/fail
  $ echo "exit 0" > /tmp/pass

  $ avocado-external-runner /bin/sh /tmp/pass /tmp/fail
  JOB ID     : 874cab7e2639f1e2244246c69a5e0d3e1afefee0
  JOB LOG    : ~/avocado/job-results/job-2022-01-19T15.33-874cab7/job.log
   (external-runner-2/2) /bin/sh-/tmp/fail: STARTED
   (external-runner-1/2) /bin/sh-/tmp/pass: STARTED
   (external-runner-2/2) /bin/sh-/tmp/fail: FAIL (0.01 s)
   (external-runner-1/2) /bin/sh-/tmp/pass: PASS (0.01 s)
  RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
  JOB HTML   : ~/avocado/job-results/job-2022-01-19T15.33-874cab7/results.html
  JOB TIME   : 1.10 s



.. note:: This example is pretty obvious and could be achieved by giving
   /tmp/pass and /tmp/fail shell “shebangs” (#!/bin/sh), making them executable
   (chmod +x /tmp/pass /tmp/fail), and running them as “SIMPLE” tests.


But now consider the following example::


  $ avocado-external-runner curl redhat.com "google.com -v"
  JOB ID     : fa68dd49a4c00e5a3c2e0fe45c6b3b0ed1b6495e
  JOB LOG    : ~/avocado/job-results/job-2022-01-19T15.37-fa68dd4/job.log
   (external-runner-2/2) /bin/curl-google.com: STARTED
   (external-runner-1/2) /bin/curl-redhat.com: STARTED
   (external-runner-2/2) /bin/curl-google.com: PASS (0.28 s)
   (external-runner-1/2) /bin/curl-redhat.com: PASS (5.39 s)
  RESULTS    : PASS 2 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
  JOB HTML   : ~/avocado/job-results/job-2022-01-19T15.37-fa68dd4/results.html
  JOB TIME   : 6.38 s


This effectively makes /bin/curl an “external test runner”, responsible for
trying to fetch those URLs, and reporting PASS or FAIL for each of them.
