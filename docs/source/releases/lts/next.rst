.. _lts_next:

============
The Next LTS
============

The Long Term Stability releases of Avocado are the result of the
accumulated changes on regular (non-LTS) releases.

This section tracks the changes introduced on each regular (non-LTS)
Avocado release, and gives a sneak preview of what will make into the
next LTS release.

What's new?
===========

When compared to the last LTS (69.x), the main changes to be
introduced by the next LTS version are:

Test Writers
------------

Test APIs
~~~~~~~~~

Utility APIs
~~~~~~~~~~~~
* Starting from this release, below cpu utils API's on left hand side
  will be deprecated and use respective ones on the right hand side.

:func:`avocado.utils.cpu.total_cpus_count` = :func:`avocado.utils.cpu.total_count`
:func:`avocado.utils.cpu._get_cpu_info` = :func:`avocado.utils.cpu._get_info`
:func:`avocado.utils.cpu._get_cpu_status` = :func:`avocado.utils.cpu._get_status`
:func:`avocado.utils.cpu.get_cpu_vendor_name` = :func:`avocado.utils.cpu.get_vendor`
:func:`avocado.utils.cpu.get_cpu_arch` = :func:`avocado.utils.cpu.get_arch`
:func:`avocado.utils.cpu.cpu_online_list` = :func:`avocado.utils.cpu.online_list`
:func:`avocado.utils.cpu.online_cpus_count` = :func:`avocado.utils.cpu.online_count`
:func:`avocado.utils.cpu.get_cpuidle_state` = :func:`avocado.utils.cpu.get_idle_state`
:func:`avocado.utils.cpu.set_cpuidle_state` = :func:`avocado.utils.cpu.set_idle_state`
:func:`avocado.utils.cpu.set_cpufreq_governor` = :func:`avocado.utils.cpu.set_freq_governor`
:func:`avocado.utils.cpu.get_cpufreq_governor` = :func:`avocado.utils.cpu.get_freq_governor`

* Additionally, :func:`avocado.utils.cpu.get_arch` implementation for
  powerpc has been corrected to return ``powerpc`` instead of cpu
  family values like ``power8``, ``power9``.
* New :func:`avocado.utils.cpu.get_family` is added to get the cpu family
  values like ``power8``, ``power9``.

Users
-----

Output Plugins
~~~~~~~~~~~~~~

* Starting from this release, `--paginator` will be a global option. You
  should add this option before any sub-command. i.e.: `avocado
  --paginator off plugins`.

* Starting from this release, `--verbose` will be a global option. You
  should add this option before any sub-command. i.e.: `avocado
  --verbose list`.

Test Loader Plugins
~~~~~~~~~~~~~~~~~~~

Varianter Plugins
~~~~~~~~~~~~~~~~~

Test Runner Plugins
~~~~~~~~~~~~~~~~~~~

Complete list of changes
========================

For a complete list of changes between the last LTS release (52.0) and
this release, please check out `the Avocado commit changelog
<https://github.com/avocado-framework/avocado/compare/69.0...master>`_.
