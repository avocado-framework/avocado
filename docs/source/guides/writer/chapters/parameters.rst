.. _test-parameter:

Test parameters
===============

.. note:: This section describes in detail what test parameters are and how
   the whole variants mechanism works in Avocado. If you're interested in the
   basics, see :ref:`accessing-test-parameter` or practical view by examples
   in :ref:`yaml-to-mux-plugin`.

Avocado allows passing parameters to tests, which effectively results in
several different variants of each test. These parameters are available in
(test's) ``self.params`` and are of
:class:`avocado.core.varianter.AvocadoParams` type. You can also access
these parameters via the configuration dict at `run.test_parameters`
namespace.

The data for ``self.params`` are supplied by
:class:`avocado.core.varianter.Varianter` which asks all registered plugins
for variants or uses default when no variants are defined.

Overall picture of how the params handling works is:

.. following figure is not really a C code, but it renders well and it
   increases the visibility.

.. code-block:: c

       +-----------+
       |           |  // Test uses AvocadoParams, with content either from
       |   Test    |  // a variant or from the test parameters given by
       |           |  // "--test-parameter"
       +-----^-----+
             |
             |
       +-----------+
       |  Runner   |  // iterates through tests and variants to run all
       +-----^-----+  // desired combinations specified by "--execution-order".
             |        // if no variants are produced by varianter plugins,
             |        // use the test parameters given by "--test-parameter"
             |
   +-------------------+ provide variants +-----------------------+
   |                   |<-----------------|                       |
   | Varianter API     |                  | Varianter plugins API |
   |                   |                  |                       |
   +-------------------+                  +-----------------------+
                                              ^
                                              |
                                              |  // All plugins are invoked
                                              |  // in turns
                                              |
                 +----------------------------+-----+
                 |                                  |
                 |                                  |
                 v                                  v
       +--------------------+           +-------------------------+
       | yaml_to_mux plugin |           | Other variant plugin(s) |
       +-----^--------------+           +-------------------------+
             |
             |  // yaml is parsed to MuxTree,
             |  // multiplexed and yields variants
       +---------------------------------+
       | +------------+ +--------------+ |
       | | --mux-yaml | | --mux-inject | |
       | +------------+ +--------------+ |
       +---------------------------------+


Let's introduce the basic keywords.

.. _tree-node:

TreeNode
~~~~~~~~

:class:`avocado.core.tree.TreeNode`

Is a node object allowing to create tree-like structures with
parent->multiple_children relations and storing params. It can
also report it's environment, which is set of params gathered
from root to this node. This is used in tests where instead of
passing the full tree only the leaf nodes are passed and their
environment represents all the values of the tree.

.. _avocado-params:
   
AvocadoParams
~~~~~~~~~~~~~

:class:`avocado.core.varianter.AvocadoParams`

Is a "database" of params present in every (instrumented) Avocado
test.  It's produced during :class:`avocado.core.test.Test`'s
``__init__`` from a `variant`_. It accepts a list of `TreeNode`_
objects; test name :class:`avocado.core.test.TestID` (for logging
purposes) and a list of default paths (`Parameter Paths`_).

In test it allows querying for data by using::

   self.params.get($name, $path=None, $default=None)

Where:

* name - name of the parameter (key)
* path - where to look for this parameter (when not specified uses mux-path)
* default - what to return when param not found

Each `variant`_ defines a hierarchy, which is preserved so `AvocadoParams`_
follows it to return the most appropriate value or raise Exception on error.

.. _parameter-paths:

Parameter Paths
~~~~~~~~~~~~~~~

As test params are organized in trees, it's possible to have the same
variant in several locations. When they are produced from the same
`TreeNode`_, it's not a problem, but when they are a different values
there is no way to distinguish which should be reported. One way is
to use specific paths, when asking for params, but sometimes, usually
when combining upstream and downstream variants, we want to get our
values first and fall-back to the upstream ones when they are not found.

For example let's say we have upstream values in ``/upstream/sleeptest``
and our values in ``/downstream/sleeptest``. If we asked for a value using
path ``"*"``, it'd raise an exception being unable to distinguish whether
we want the value from ``/downstream`` or ``/upstream``. We can set the
parameter paths to ``["/downstream/*", "/upstream/*"]`` to make all relative
calls (path starting with ``*``) to first look in nodes in ``/downstream``
and if not found look into ``/upstream``.

More practical overview of parameter paths is in :ref:`yaml-to-mux-plugin`
in :ref:`yaml-to-mux-resolution-order` section.

Variant
~~~~~~~

Variant is a set of params produced by `Varianter`_s and passed to the
test by the test runner as ``params`` argument. The simplest variant
is ``None``, which still produces an empty `AvocadoParams`_. Also, the
`Variant`_ can also be a ``tuple(list, paths)`` or just the
``list`` of :class:`avocado.core.tree.TreeNode` with the params.

Dumping/Loading Variants
~~~~~~~~~~~~~~~~~~~~~~~~

Depending on the number of parameters, generating the Variants can be very
compute intensive. As the Variants are generated as part of the Job execution,
that compute intensive task will be executed by the systems under test, causing
a possibly unwanted cpu load on those systems.

To avoid such situation, you can acquire the resulting JSON serialized variants
file, generated out of the variants computation, and load that file on the
system where the Job will be executed.

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

Once you have the ``variants.json`` file, you can load it on the system where
the Job will take place::

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

.. _varianter:

Varianter
~~~~~~~~~

:class:`avocado.core.varianter.Varianter`

Is an internal object which is used to interact with the variants mechanism
in Avocado. It's lifecycle is compound of two stages. First it allows
the core/plugins to inject default values, then it is parsed and
only allows querying for values, number of variants and such.

Example workflow of `avocado run passtest.py -m example.yaml` is::

   avocado run passtest.py -m example.yaml
     |
     + parser.finish -> Varianter.__init__  // dispatcher initializes all plugins
     |
     + job.run_tests -> Varianter.is_parsed
     |
     + job.run_tests -> Varianter.parse
     |                     // processes default params
     |                     // initializes the plugins
     |                     // updates the default values
     |
     + job._log_variants -> Varianter.to_str  // prints the human readable representation to log
     |
     + runner.run_suite -> Varianter.get_number_of_tests
     |
     + runner._iter_variants -> Varianter.itertests  // Yields variants

In order to allow force-updating the `Varianter`_ it supports
``ignore_new_data``, which can be used to ignore new data. This is used
by `Replay` to replace the current run `Varianter`_ with the one
loaded from the replayed job. The workflow with ``ignore_new_data`` could
look like this::

   avocado run --replay latest -m example.yaml
     |
     + replay.run -> Varianter.is_parsed
     |
     + replay.run  // Varianter object is replaced with the replay job's one
     |             // Varianter.ignore_new_data is set
     |
     + job.run_tests -> Varianter.is_parsed
     |
     + job._log_variants -> Varianter.to_str
     |
     + runner.run_suite -> Varianter.get_number_of_tests
     |
     + runner._iter_variants -> Varianter.itertests

The `Varianter`_ itself can only produce an empty variant, but it invokes all 
`Varianter plugins`_ and if any of them reports variants it yields them 
instead of the default variant.



Test parameters
~~~~~~~~~~~~~~~

This is an Avocado core feature, that is, it's not dependent on any
varianter plugin.  In fact, it's only active when no Varianter plugin
is used and produces a valid variant.

Avocado will use those simple parameters, and will pass them to all
tests in a job execution.  This is done on the command line via
``--test-parameter``, or simply, ``-p``.  It can be given multiple
times for multiple parameters.

Because Avocado parameters do not have a mechanism to define their
types, test code should always consider that a parameter value is a
string, and convert it to the appropriate type.

.. note:: Some varianter plugins would implicitly set parameters
   with different data types, but given that the same test can be
   used with different, or none, varianter plugins, it's safer if
   the test does an explicit check or type conversion.

Because the :class:`avocado.core.varianter.AvocadoParams` mandates the
concept of a parameter path (a legacy of the tree based Multiplexer)
and these test parameters are flat, those test parameters are placed
in the ``/`` path.  This is to ensure maximum compatibility with tests
that do not choose an specific parameter location.

.. _varianter-plugins:

Varianter plugins
~~~~~~~~~~~~~~~~~

:class:`avocado.core.plugin_interfaces.Varianter`

A plugin interface that can be used to build custom plugins which
are used by `Varianter`_ to get test variants. For inspiration see
:class:`avocado_varianter_yaml_to_mux.YamlToMux` which is an
optional varianter plugin. Details about this plugin can be
found here :ref:`yaml-to-mux-plugin`.
