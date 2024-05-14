==========================
Writing an Executable Test
==========================

This very simple example of an executable test in shell script::

    $ echo '#!/bin/bash' > /tmp/executable_test.sh
    $ echo 'exit 0' >> /tmp/executable_test.sh
    $ chmod +x /tmp/executable_test.sh

Notice that the file is given executable permissions, which is a
requirement for Avocado to treat it as a executable test. Also notice
that the script exits with status code 0, which signals a successful
result to Avocado.

BASH extensions for Executable tests
------------------------------------

Exec-tests written in shell can use a few Avocado utilities.  In your
shell code, check if the libraries are available with something like::

  AVOCADO_SHELL_EXTENSIONS_DIR=$(avocado exec-path 2>/dev/null)

And if available, injects that directory containing those utilities
into the PATH used by the shell, making those utilities readily
accessible::

  if [ $? == 0 ]; then
    PATH=$AVOCADO_SHELL_EXTENSIONS_DIR:$PATH
  fi

For a full list of utilities, take a look into at the directory return
by ``avocado exec-path`` (if any).  Also, the example test
``examples/tests/simplewarning.sh`` can serve as further inspiration:

.. literalinclude:: ../../../../../examples/tests/simplewarning.sh

.. tip:: These extensions may be available as a separate package.  For
         RPM packages, look for the ``bash`` sub-package.

Environment Variables for Tests
-------------------------------

Avocado's environment variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Avocado exports some information, including test parameters, as environment
variables to the running test. Here is a list of the variables that Avocado
currently exports to exec-test tests in default:

+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| Environment Variable        | Meaning                               | Example                                                                                             |
+=============================+=======================================+=====================================================================================================+
| AVOCADO_VERSION             | Version of Avocado test runner        | 92.0                                                                                                |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| AVOCADO_TEST_BASEDIR        | Base directory of Avocado tests. More | $HOME/src/avocado/avocado.dev/examples/tests                                                        |
|                             | info in :data:`avocado.Test.basedir`  |                                                                                                     |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| AVOCADO_TEST_WORKDIR        | Work directory for the test. More     | /var/tmp/.avocado-taskcx8of8di/test-results/tmp_dirfgqrnbu/1-Env.test                               |
|                             | info in :data:`avocado.Test.workdir`  |                                                                                                     |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| AVOCADO_TESTS_COMMON_TMPDIR | Temporary directory created by the    | /var/tmp/avocado_XhEdo/                                                                             |
|                             | :ref:`plugin_teststmpdir` plugin.  The|                                                                                                     |
|                             | directory is persistent throughout the|                                                                                                     |
|                             | tests in the same Job                 |                                                                                                     |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| AVOCADO_TEST_LOGDIR         | Log directory for the test            | /var/tmp/.avocado-task_5t_srpn/test-results/1-Env.test                                              |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| AVOCADO_TEST_LOGFILE        | Log file for the test                 | /var/tmp/.avocado-taskcx8of8di/test-results/1-Env.test/debug.log                                    |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| AVOCADO_TEST_OUTPUTDIR      | Output directory for the test         | /var/tmp/.avocado-taskcx8of8di/test-results/1-Env.test/data                                         |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+
| `***`                       | All variables from --mux-yaml         | TIMEOUT=60; IO_WORKERS=10; VM_BYTES=512M; ...                                                       |
+-----------------------------+---------------------------------------+-----------------------------------------------------------------------------------------------------+

User's environment variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can also let avocado set your own environment variables. For that, you need
to pass the environment variables as keyword arguments (``kwargs``) to the exec-tests.
Here is an example of Job API which passes ``SLEEP_LENGTH`` to sleeptest.sh to set
the time for which the test should sleep:

.. literalinclude:: ../../../../../examples/jobs/custom_exec_test.py

And now we can see that sleeptest.sh can use  ``SLEEP_LENGTH`` environment
variable:

.. literalinclude:: ../../../../../examples/tests/sleeptest.sh

.. note:: All environment variables set by avocado will be accessible only during
          the test runtime and it won't change your environment.

Disabling environment variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Let's imagine that your testing environment has some important variables, but they
could have a negative impact on one of your tests. In that case, avocado lets you
disable those variables during the test runtime. To disable a test variable,
you need to set it in test ``kwargs`` to ``None``  like this::

  Runnable("exec-test", "examples/tests/sleeptest.sh", SLEEP_LENGTH=None)

If you need to clear the whole environment before your test, then you can set
``runner.exectest.clear_env`` config variable. This variable has two options.
``system`` and ``all``. If you use ``system`` option the testing environment
will have only Avocado default variables and variables from test ``kwargs``.
If you use ``all`` option, the testing environment will have only variables
from test ``kwargs``::

  Runnable("exec-test", "examples/tests/sleeptest.sh", config={'runner.exectest.clear_env': system}, SLEEP_LENGTH=1)
