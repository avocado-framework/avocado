==================
Welcome to Avocado
==================

Avocado is a set of tools and libraries to help with automated testing.

One can call it a test framework with benefits.  Native tests are written in
Python and they follow the ``unittest`` pattern, but any executable can
serve as a test.

How does it work?
=================

You should first experience Avocado by using the test runner, that is, the
command line tool that will conveniently run your tests and collect their
results.

To do so, please run ``avocado`` with the ``run`` sub-command followed by a
test reference, which could be either a path to the file, or a recognizable
name::

    $ avocado run /bin/true
    JOB ID     : 3a5c4c51ceb5369f23702efb10b4209b111141b2
    JOB LOG    : $HOME/avocado/job-results/job-2019-10-31T10.34-3a5c4c5/job.log
     (1/1) /bin/true: PASS (0.04 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 0.15 s

You probably noticed that we used ``/bin/true`` as a test, and in accordance
with our expectations, it passed! These are known as **simple tests**, but there
is also another type of test, which we call **instrumented tests**.

.. tip:: See more at the `Test types`_ section on the `Avocado User's Guide`_.

Why should I use it?
====================

Multiple result formats
-----------------------

A regular run of Avocado will present the test results on standard output, a
nice and colored report useful for human beings. But results for machines can
also be generated.

Check the job-results folder (``$HOME/avocado/job-results/latest/``) to see the
outputs.

Currently we support, out of box, the following output formats:

* **xUnit**: an XML format that contains test results in a structured form,
  and are used by other test automation projects, such as jenkins.

* **JSON**: a widely used data exchange format. The JSON Avocado plugin
  outputs job information, similarly to the xunit output plugin.

* **TAP**: Provides the basic TAP (`Test Anything Protocol`_) results,
  currently in v12. Unlike most existing Avocado machine readable outputs
  this one is streamlined (per test results).

.. note:: You can see the results of the latest job inside the folder
  ``$HOME/avocado/job-results/latest/``. You can also specify at the command line
  the options ``--xunit``, ``--json`` or ``--tap`` followed by a filename.
  Avocado will write the output on the specified filename.

When it comes to outputs, Avocado is very flexible. You can check the various
**output plugins**. If you need something more sophisticated, visit our `plugins
section`_.

Sysinfo data collector
----------------------

Avocado comes with a sysinfo plugin, which automatically gathers some system
information per each job or even between tests. This is very helpful when
trying to identify the cause of a test failure.

Check out the files stored at ``$HOME/avocado/job-results/latest/sysinfo/``::

  $ ls $HOME/avocado/job-results/latest/sysinfo/pre/
  'brctl show'           hostname             modules
   cmdline              'ifconfig -a'         mounts
   cpuinfo               installed_packages  'numactl --hardware show'
   current_clocksource   interrupts           partitions
  'df -mP'              'ip link'             scaling_governor
   dmesg                'ld --version'       'uname -a'
   dmidecode             lscpu                uptime
  'fdisk -l'            'lspci -vvnn'         version
  'gcc --version'        meminfo


For more information about sysinfo collector, please consult the `Avocado User's Guide`_.

Job Replay and Job Diff
-----------------------

In order to reproduce a given job using the same data, one can use the
``replay`` subcommand, informing the hash id from the original job to be
replayed. The hash id can be partial, as long as the provided part corresponds
to the initial characters of the original job id and it is also unique enough.
Or, instead of the job id, you can use the string latest and Avocado will
replay the latest job executed.

Example::

     $ avocado replay 825b86
     JOB ID     : 55a0d10132c02b8cc87deb2b480bfd8abbd956c3
     SRC JOB ID : 825b860b0c2f6ec48953c638432e3e323f8d7cad
     JOB LOG    : $HOME/avocado/job-results/job-2016-01-11T16.18-55a0d10/job.log
      (1/2) /bin/true: PASS (0.01 s)
      (2/2) /bin/false: FAIL (0.01 s)
     RESULTS    : PASS 1 | ERROR 0 | FAIL 1 | SKIP 0 | WARN 0 | INTERRUPT 0
     JOB TIME   : 0.11 s
     JOB HTML   : $HOME/avocado/job-results/job-2016-01-11T16.18-55a0d10/html/results.html

Avocado Diff plugin allows users to easily compare several aspects of two given
jobs. The basic usage is:

.. code-block:: diff

    $ avocado diff 7025aaba 384b949c
    --- 7025aaba9c2ab8b4bba2e33b64db3824810bb5df
    +++ 384b949c991b8ab324ce67c9d9ba761fd07672ff
    @@ -1,15 +1,15 @@

     COMMAND LINE
    -/usr/bin/avocado run sleeptest.py
    +/usr/bin/avocado run passtest.py

     TOTAL TIME
    -1.00 s
    +0.00 s

     TEST RESULTS
    -1-sleeptest.py:SleepTest.test: PASS
    +1-passtest.py:PassTest.test: PASS

     ...


Extensible by plugins
---------------------

Avocado has a plugin system that can be used to extend it in a clean way. The
``avocado`` command line tool has a builtin ``plugins`` command that lets you
list available plugins. The usage is pretty simple::

 $ avocado plugins
 Plugins that add new commands (avocado.plugins.cli.cmd):
 exec-path Returns path to Avocado bash libraries and exits.
 run       Run one or more tests (native test, test alias, binary or script)
 sysinfo   Collect system information
 ...
 Plugins that add new options to commands (avocado.plugins.cli):
 remote  Remote machine options for 'run' subcommand
 journal Journal options for the 'run' subcommand
 ...

For more information about plugins, please visit the `Plugin System`_ section on
the `Avocado User's Guide`_.

Utility libraries
-----------------

When writing tests, developers often need to perform basic tasks on OS and end
up having to implement these routines just to run they tests.

Avocado has **more than 40** *utility modules* that helps you to perform basic
operations.

Below a small subset of our utility modules:

* **utils.vmimage**: This utility provides a API to download/cache VM images
  (QCOW) from the official distributions repositories.
* **utils.memory**: Provides information about memory usage.
* **utils.cpu**: Get information from the current's machine CPU.
* **utils.software_manager**: Software package management library.
* **utils.download**: Methods to download URLs and regular files.
* **utils.archive**: Module to help extract and create compressed archives.

Avocado Python API
==================

If the command-line is limiting you, then you can use our new API and
create custom jobs and test suites:

.. code-block:: python

  import sys

  from avocado.core.job import Job

  with Job.from_config({'resolver.references': ['/bin/true']}) as job:
      sys.exit(job.run())

How to install
==============

It is super easy, just run the follow command::

    $ pip3 install --user avocado-framework

This will install the avocado command in your home directory.

.. note:: For more details and alternative methods, please visit the
         `Installing section on Avocado User’s Guide`_

Documentation
=============

Please use the following links for full documentation, including installation
methods, tutorials and API or browse this site for more content.

* `latest release <https://avocado-framework.readthedocs.io/>`_

* `development version <https://avocado-framework.readthedocs.io/en/latest/>`_

Bugs/Requests
=============

Please use the `GitHub issue tracker`_ to submit bugs or request features.

Changelog
=========

Please consult the `Avocado Releases`_ for fixes and enhancements of each version.

License
=======

Except where otherwise indicated in a given source file, all original
contributions to Avocado are licensed under the GNU General Public License
version 2 `(GPLv2) <https://www.gnu.org/licenses/gpl-2.0.html>`_ or any later
version.

By contributing you agree that these contributions are your own (or approved by
your employer) and you grant a full, complete, irrevocable copyright license to
all users and developers of the Avocado project, present and future, pursuant
to the license of the project.

Build and Quality Status
========================

.. image:: https://copr.fedorainfracloud.org/coprs/g/avocado/avocado-latest/package/python-avocado/status_image/last_build.png
   :target: https://copr.fedorainfracloud.org/coprs/g/avocado/avocado-latest/package/python-avocado/
   :alt: Copr build

.. image:: https://api.cirrus-ci.com/github/avocado-framework/avocado.svg
   :target: https://cirrus-ci.com/github/avocado-framework/avocado
   :alt: Basic checks on Cirrus CI

.. image:: https://img.shields.io/lgtm/alerts/g/avocado-framework/avocado.svg?logo=lgtm&logoWidth=18
   :target: https://lgtm.com/projects/g/avocado-framework/avocado/alerts/
   :alt: lgtm total alerts

.. image:: https://api.codeclimate.com/v1/badges/03f506164e1d19f95480/maintainability
   :target: https://codeclimate.com/github/avocado-framework/avocado/maintainability
   :alt: Code Climate Maintainability

.. image:: https://img.shields.io/lgtm/grade/python/g/avocado-framework/avocado.svg?logo=lgtm&logoWidth=18
   :target: https://lgtm.com/projects/g/avocado-framework/avocado/context:python
   :alt: lgtm language grade for Python

.. image:: https://img.shields.io/lgtm/grade/javascript/g/avocado-framework/avocado.svg?logo=lgtm&logoWidth=18
   :target: https://lgtm.com/projects/g/avocado-framework/avocado/context:javascript
   :alt: lgtm language grade for JavaScript

.. image:: https://readthedocs.org/projects/avocado-framework/badge/?version=latest
   :target: https://avocado-framework.readthedocs.io/en/latest/
   :alt: Documentation Status


.. _Avocado User's Guide: https://avocado-framework.readthedocs.io/en/latest/guides/user/index.html
.. _Installing section on Avocado User’s Guide: https://avocado-framework.readthedocs.io/en/latest/guides/user/chapters/installing.html#installing
.. _Test types: https://avocado-framework.readthedocs.io/en/latest/guides/user/chapters/concepts.html#test-types
.. _plugins section: https://avocado-framework.readthedocs.io/en/latest/plugins/index.html
.. _Plugin System: https://avocado-framework.readthedocs.io/en/latest/guides/user/chapters/plugins.html
.. _Avocado Releases: https://avocado-framework.readthedocs.io/en/latest/releases/index.html
.. _GitHub issue tracker: https://github.com/avocado-framework/avocado/issues
.. _Test Anything Protocol: https://testanything.org/
