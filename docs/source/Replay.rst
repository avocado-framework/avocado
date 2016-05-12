.. _job_replay_:

==========
Job Replay
==========

In order to reproduce a given job using the same data, one can use the
``--replay`` option for the ``run`` command, informing the hash id from
the original job to be replayed. The hash id can be partial, as long as
the provided part corresponds to the inital characters of the original
job id and it is also unique enough.

Let's see an example. First, running a simple job with two urls::

     $ avocado run /bin/true /bin/false
     JOB ID     : 825b860b0c2f6ec48953c638432e3e323f8d7cad
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T16.14-825b860/job.log
     TESTS      : 2
      (1/2) /bin/true: PASS (0.01 s)
      (2/2) /bin/false: FAIL (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T16.14-825b860/html/results.html
     TESTS TIME : 0.02 s

Now we can replay the job by running::

     $ avocado run --replay 825b86
     JOB ID     : 55a0d10132c02b8cc87deb2b480bfd8abbd956c3
     SRC JOB ID : 825b860b0c2f6ec48953c638432e3e323f8d7cad
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T16.18-55a0d10/job.log
     TESTS      : 2
      (1/2) /bin/true: PASS (0.01 s)
      (2/2) /bin/false: FAIL (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T16.18-55a0d10/html/results.html
     TESTS TIME : 0.01 s

The replay feature will retrieve the original job urls, the multiplex
tree and the configuration. Let's see another example, now using
multiplex file::

     $ avocado run /bin/true /bin/false --multiplex mux-environment.yaml
     JOB ID     : bd6aa3b852d4290637b5e771b371537541043d1d
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T21.56-bd6aa3b/job.log
     TESTS      : 48
      (1/48) /bin/true;1: PASS (0.01 s)
      (2/48) /bin/true;2: PASS (0.01 s)
      (3/48) /bin/true;3: PASS (0.01 s)
      (4/48) /bin/true;4: PASS (0.01 s)
      (5/48) /bin/true;5: PASS (0.01 s)
      (6/48) /bin/true;6: PASS (0.01 s)
      (7/48) /bin/true;7: PASS (0.01 s)
      (8/48) /bin/true;8: PASS (0.01 s)
      (9/48) /bin/true;9: PASS (0.01 s)
      (10/48) /bin/true;10: PASS (0.01 s)
      (11/48) /bin/true;11: PASS (0.01 s)
      (12/48) /bin/true;12: PASS (0.01 s)
      (13/48) /bin/true;13: PASS (0.01 s)
      (14/48) /bin/true;14: PASS (0.01 s)
      (15/48) /bin/true;15: PASS (0.01 s)
      (16/48) /bin/true;16: PASS (0.01 s)
      (17/48) /bin/true;17: PASS (0.01 s)
      (18/48) /bin/true;18: PASS (0.01 s)
      (19/48) /bin/true;19: PASS (0.01 s)
      (20/48) /bin/true;20: PASS (0.01 s)
      (21/48) /bin/true;21: PASS (0.01 s)
      (22/48) /bin/true;22: PASS (0.01 s)
      (23/48) /bin/true;23: PASS (0.01 s)
      (24/48) /bin/true;24: PASS (0.01 s)
      (25/48) /bin/false;1: FAIL (0.01 s)
      (26/48) /bin/false;2: FAIL (0.01 s)
      (27/48) /bin/false;3: FAIL (0.01 s)
      (28/48) /bin/false;4: FAIL (0.01 s)
      (29/48) /bin/false;5: FAIL (0.01 s)
      (30/48) /bin/false;6: FAIL (0.01 s)
      (31/48) /bin/false;7: FAIL (0.01 s)
      (32/48) /bin/false;8: FAIL (0.01 s)
      (33/48) /bin/false;9: FAIL (0.01 s)
      (34/48) /bin/false;10: FAIL (0.01 s)
      (35/48) /bin/false;11: FAIL (0.01 s)
      (36/48) /bin/false;12: FAIL (0.01 s)
      (37/48) /bin/false;13: FAIL (0.01 s)
      (38/48) /bin/false;14: FAIL (0.01 s)
      (39/48) /bin/false;15: FAIL (0.01 s)
      (40/48) /bin/false;16: FAIL (0.01 s)
      (41/48) /bin/false;17: FAIL (0.01 s)
      (42/48) /bin/false;18: FAIL (0.01 s)
      (43/48) /bin/false;19: FAIL (0.01 s)
      (44/48) /bin/false;20: FAIL (0.01 s)
      (45/48) /bin/false;21: FAIL (0.01 s)
      (46/48) /bin/false;22: FAIL (0.01 s)
      (47/48) /bin/false;23: FAIL (0.01 s)
      (48/48) /bin/false;24: FAIL (0.01 s)
     RESULTS    : PASS 24 | ERROR 0 | FAIL 24 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T21.56-bd6aa3b/html/results.html
     TESTS TIME : 0.29 s

We can replay the job as is, using ``$ avocado run --replay bd6aa3b``,
or replay the job ignoring the multiplex file, as below::

     $ avocado run --replay bd6aa3b --replay-ignore mux
     Ignoring multiplex from source job with --replay-ignore.
     JOB ID     : d5a46186ee0fb4645e3f7758814003d76c980bf9
     SRC JOB ID : bd6aa3b852d4290637b5e771b371537541043d1d
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T22.01-d5a4618/job.log
     TESTS      : 2
      (1/2) /bin/true: PASS (0.01 s)
      (2/2) /bin/false: FAIL (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T22.01-d5a4618/html/results.html
     TESTS TIME : 0.02 s

Also, it is possible to replay only the variants that faced a given
result, using the option ``--replay-test-status``. Using the same job
``bd6aa3b``, see the example below::

    $ avocado run --replay bd6aa3b --replay-test-status FAIL
    JOB ID     : 2e1dc41af6ed64895f3bb45e3820c5cc62a9b6eb
    SRC JOB ID : bd6aa3b852d4290637b5e771b371537541043d1d
    JOB LOG    : $HOME/avocado/job-results/job-2016-01-12T00.38-2e1dc41/job.log
    TESTS      : 48
     (1/48) /bin/true;1: SKIP
     (2/48) /bin/true;2: SKIP
     (3/48) /bin/true;3: SKIP
     (4/48) /bin/true;4: SKIP
     (5/48) /bin/true;5: SKIP
     (6/48) /bin/true;6: SKIP
     (7/48) /bin/true;7: SKIP
     (8/48) /bin/true;8: SKIP
     (9/48) /bin/true;9: SKIP
     (10/48) /bin/true;10: SKIP
     (11/48) /bin/true;11: SKIP
     (12/48) /bin/true;12: SKIP
     (13/48) /bin/true;13: SKIP
     (14/48) /bin/true;14: SKIP
     (15/48) /bin/true;15: SKIP
     (16/48) /bin/true;16: SKIP
     (17/48) /bin/true;17: SKIP
     (18/48) /bin/true;18: SKIP
     (19/48) /bin/true;19: SKIP
     (20/48) /bin/true;20: SKIP
     (21/48) /bin/true;21: SKIP
     (22/48) /bin/true;22: SKIP
     (23/48) /bin/true;23: SKIP
     (24/48) /bin/true;24: SKIP
     (25/48) /bin/false;1: FAIL (0.01 s)
     (26/48) /bin/false;2: FAIL (0.01 s)
     (27/48) /bin/false;3: FAIL (0.01 s)
     (28/48) /bin/false;4: FAIL (0.01 s)
     (29/48) /bin/false;5: FAIL (0.01 s)
     (30/48) /bin/false;6: FAIL (0.01 s)
     (31/48) /bin/false;7: FAIL (0.01 s)
     (32/48) /bin/false;8: FAIL (0.01 s)
     (33/48) /bin/false;9: FAIL (0.01 s)
     (34/48) /bin/false;10: FAIL (0.01 s)
     (35/48) /bin/false;11: FAIL (0.01 s)
     (36/48) /bin/false;12: FAIL (0.01 s)
     (37/48) /bin/false;13: FAIL (0.01 s)
     (38/48) /bin/false;14: FAIL (0.01 s)
     (39/48) /bin/false;15: FAIL (0.01 s)
     (40/48) /bin/false;16: FAIL (0.01 s)
     (41/48) /bin/false;17: FAIL (0.01 s)
     (42/48) /bin/false;18: FAIL (0.01 s)
     (43/48) /bin/false;19: FAIL (0.01 s)
     (44/48) /bin/false;20: FAIL (0.01 s)
     (45/48) /bin/false;21: FAIL (0.01 s)
     (46/48) /bin/false;22: FAIL (0.01 s)
     (47/48) /bin/false;23: FAIL (0.01 s)
     (48/48) /bin/false;24: FAIL (0.01 s)
    RESULTS    : PASS 0 | ERROR 0 | FAIL 24 | SKIP 24 | WARN 0 | INTERRUPT 0
    JOB HTML   : $HOME/avocado/job-results/job-2016-01-12T00.38-2e1dc41/html/results.html
    TESTS TIME : 0.19 s

To be able to replay a job, avocado records the job data in the same
job results directory, inside a subdirectory named ``replay``. If a
given job has a non-default path to record the logs, when the replay
time comes, we need to inform where the logs are. See the example
below::

     $ avocado run /bin/true --job-results-dir /tmp/avocado_results/
     JOB ID     : f1b1c870ad892eac6064a5332f1bbe38cda0aaf3
     JOB LOG    : /tmp/avocado_results/job-2016-01-11T22.10-f1b1c87/job.log
     TESTS      : 1
      (1/1) /bin/true: PASS (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB HTML   : /tmp/avocado_results/job-2016-01-11T22.10-f1b1c87/html/results.html
     TESTS TIME : 0.01 s

Trying to replay the job, it fails::

     $ avocado run --replay f1b1
     can't find job results directory in '$HOME/avocado/job-results'

In this case, we have to inform where the job results dir is located::

     $ avocado run --replay f1b1 --replay-data-dir /tmp/avocado_results
     JOB ID     : 19c76abb29f29fe410a9a3f4f4b66387570edffa
     SRC JOB ID : f1b1c870ad892eac6064a5332f1bbe38cda0aaf3
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T22.15-19c76ab/job.log
     TESTS      : 1
      (1/1) /bin/true: PASS (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T22.15-19c76ab/html/results.html
     TESTS TIME : 0.01 s
