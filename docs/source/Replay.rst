.. _job_replay_:

==========
Job Replay
==========

In order to reproduce a given job using the same data, one can use the
``--replay`` option for the ``run`` command, informing the hash id from
the original job to be replayed. The hash id can be partial, as long as
the provided part corresponds to the initial characters of the original
job id and it is also unique enough. Or, instead of the job id, you can
use the string ``latest`` and avocado will replay the latest job executed.

Let's see an example. First, running a simple job with two test references::

     $ avocado run /bin/true /bin/false
     JOB ID     : 825b860b0c2f6ec48953c638432e3e323f8d7cad
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T16.14-825b860/job.log
      (1/2) /bin/true: PASS (0.01 s)
      (2/2) /bin/false: FAIL (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB TIME   : 0.12 s
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T16.14-825b860/html/results.html

Now we can replay the job by running::

     $ avocado run --replay 825b86
     JOB ID     : 55a0d10132c02b8cc87deb2b480bfd8abbd956c3
     SRC JOB ID : 825b860b0c2f6ec48953c638432e3e323f8d7cad
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T16.18-55a0d10/job.log
      (1/2) /bin/true: PASS (0.01 s)
      (2/2) /bin/false: FAIL (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB TIME   : 0.11 s
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T16.18-55a0d10/html/results.html

The replay feature will retrieve the original test references, the variants
and the configuration. Let's see another example, now using a
mux YAML file::

     $ avocado run /bin/true /bin/false --mux-yaml mux-environment.yaml
     JOB ID     : bd6aa3b852d4290637b5e771b371537541043d1d
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T21.56-bd6aa3b/job.log
      (1/4) /bin/true+first-c49a: PASS (0.01 s)
      (2/4) /bin/true+second-f05f: PASS (0.01 s)
      (3/4) /bin/false+first-c49a: FAIL (0.04 s)
      (4/4) /bin/false+second-f05f: FAIL (0.04 s)
     RESULTS    : PASS 2 | ERROR 0 | FAIL 2 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB TIME   : 0.19 s
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T21.56-bd6aa3b/html/results.html

We can replay the job as is, using ``$ avocado run --replay latest``,
or replay the job ignoring the variants, as below::

     $ avocado run --replay bd6aa3b --replay-ignore variants
     Ignoring variants from source job with --replay-ignore.
     JOB ID     : d5a46186ee0fb4645e3f7758814003d76c980bf9
     SRC JOB ID : bd6aa3b852d4290637b5e771b371537541043d1d
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T22.01-d5a4618/job.log
      (1/2) /bin/true: PASS (0.01 s)
      (2/2) /bin/false: FAIL (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB TIME   : 0.12 s
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T22.01-d5a4618/html/results.html

Also, it is possible to replay only the variants that faced a given
result, using the option ``--replay-test-status``. See the example below::

    $ avocado run --replay bd6aa3b --replay-test-status FAIL
    JOB ID     : 2e1dc41af6ed64895f3bb45e3820c5cc62a9b6eb
    SRC JOB ID : bd6aa3b852d4290637b5e771b371537541043d1d
    JOB LOG    : $HOME/avocado/job-results/job-2016-01-12T00.38-2e1dc41/job.log
     (1/4) /bin/true+first-c49a: SKIP
     (2/4) /bin/true+second-f05f: SKIP
     (3/4) /bin/false+first-c49a: FAIL (0.03 s)
     (4/4) /bin/false+second-f05f: FAIL (0.04 s)
    RESULTS    : PASS 0 | ERROR 0 | FAIL 24 | SKIP 24 | WARN 0 | INTERRUPT 0
    JOB TIME   : 0.29 s
    JOB HTML   : $HOME/avocado/job-results/job-2016-01-12T00.38-2e1dc41/html/results.html

Of which one special example is ``--replay-test-status INTERRUPTED``
or simply ``--replay-resume``, which SKIPs the executed
tests and only executes the ones which were CANCELED or not executed
after a CANCELED test. This feature should work even on hard interruptions
like system crash.

When replaying jobs that were executed with the ``--failfast on`` option, you
can disable the ``failfast`` option using ``--failfast off`` in the replay job.

To be able to replay a job, avocado records the job data in the same
job results directory, inside a subdirectory named ``replay``. If a
given job has a non-default path to record the logs, when the replay
time comes, we need to inform where the logs are. See the example
below::

     $ avocado run /bin/true --job-results-dir /tmp/avocado_results/
     JOB ID     : f1b1c870ad892eac6064a5332f1bbe38cda0aaf3
     JOB LOG    : /tmp/avocado_results/job-2016-01-11T22.10-f1b1c87/job.log
      (1/1) /bin/true: PASS (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB TIME   : 0.11 s
     JOB HTML   : /tmp/avocado_results/job-2016-01-11T22.10-f1b1c87/html/results.html

Trying to replay the job, it fails::

     $ avocado run --replay f1b1
     can't find job results directory in '$HOME/avocado/job-results'

In this case, we have to inform where the job results directory is located::

     $ avocado run --replay f1b1 --replay-data-dir /tmp/avocado_results
     JOB ID     : 19c76abb29f29fe410a9a3f4f4b66387570edffa
     SRC JOB ID : f1b1c870ad892eac6064a5332f1bbe38cda0aaf3
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T22.15-19c76ab/job.log
      (1/1) /bin/true: PASS (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB TIME   : 0.11 s
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T22.15-19c76ab/html/results.html
