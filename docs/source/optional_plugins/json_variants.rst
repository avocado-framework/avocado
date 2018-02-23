.. _json_variants:

JSON Variants plugin
====================

:mod:`avocado_json_variants`

This plugin enables Avocado to load the variants from a JSON serialized file.

Acquiring the JSON serialized variants file
-------------------------------------------

There are two ways to acquire the JSON serialized variants file:

- Using the ``--json-variants-dump`` option of the ``avocado variants``
  command::

    $ avocado variants --mux-yaml examples/yaml_to_mux/hw/hw.yaml --json-variants-dump variants.json
    ...

    $ file variants.json
    variants.json: ASCII text, with very long lines, with no line terminators

- Getting the auto-generated JSON serialized variants file after a Avocado Job
  execution::

    $ avocado run passtest.py --mux-yaml examples/yaml_to_mux/hw/hw.yaml
    ...

    $ file $HOME/avocado/job-results/latest/jobdata/variants.json
    $HOME/avocado/job-results/latest/jobdata/variants.json: ASCII text, with very long lines, with no line terminators

Using the JSON Variants Plugin
------------------------------

To load the JSON serialized variants file to an Avocado Job, use the
``--json-variants-load`` option::

    $ avocado run passtest.py --json-variants-load variants.json
    JOB ID     : f2022736b5b89d7f4cf62353d3fb4d7e3a06f075
    JOB LOG    : $HOME/avocado/job-results/job-2018-02-09T14.39-f202273/job.log
     (1/6) passtest.py:PassTest.test;intel-scsi-56d0: PASS (0.04 s)
     (2/6) passtest.py:PassTest.test;intel-virtio-3d4e: PASS (0.02 s)
     (3/6) passtest.py:PassTest.test;amd-scsi-fa43: PASS (0.02 s)
     (4/6) passtest.py:PassTest.test;amd-virtio-a59a: PASS (0.02 s)
     (5/6) passtest.py:PassTest.test;arm-scsi-1c14: PASS (0.03 s)
     (6/6) passtest.py:PassTest.test;arm-virtio-5ce1: PASS (0.04 s)
    RESULTS    : PASS 6 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 0.51 s
    JOB HTML   : $HOME/avocado/job-results/job-2018-02-09T14.39-f202273/results.html