==================
Sysinfo collection
==================

Avocado comes with a ``sysinfo`` plugin, which automatically gathers some
system information per each job or even between tests. This is very useful
when later we want to know what caused the test's failure. This system
is configurable but we provide a sane set of defaults for you.

In the default Avocado configuration (``/etc/avocado/avocado.conf``) there
is a section ``sysinfo.collect`` where you can enable/disable the sysinfo
collection as well as configure the basic environment. In
``sysinfo.collectibles`` section you can define basic paths of where
to look for what commands/tasks should be performed before/during
the sysinfo collection. Avocado supports three types of tasks:

1. commands - file with new-line separated list of commands to be executed
   before and after the job/test (single execution commands). It is possible
   to set a timeout which is enforced per each executed command in
   [sysinfo.collect] by setting "commands_timeout" to a positive number.
2. files - file with new-line separated list of files to be copied
3. profilers - file with new-line separated list of commands to be executed
   before the job/test and killed at the end of the job/test (follow-like
   commands)

Additionally this plugin tries to follow the system log via ``journalctl``
if available.

By default these are collected per-job but you can also run them per-test by
setting ``per_test = True`` in the ``sysinfo.collect`` section.

The sysinfo can also be enabled/disabled on the cmdline if needed by
``--sysinfo on|off``.

After the job execution you can find the collected information in
``$RESULTS/sysinfo`` of ``$RESULTS/test-results/$TEST/sysinfo``. They
are categorized into ``pre``, ``post`` and ``profile`` folders and
the filenames are safely-escaped executed commands or file-names.
You can also see the sysinfo in html results when you have html
results plugin enabled.

.. warning:: If you are using avocado from sources, you need to manually place
   the ``commands``/``files``/``profilers`` into the ``/etc/avocado/sysinfo``
   directories or adjust the paths in
   ``$AVOCADO_SRC/etc/avocado/avocado.conf``.
