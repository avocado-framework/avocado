Writing an Executable Test
--------------------------

This very simple example of an executable test in shell script::

    $ echo '#!/bin/bash' > /tmp/executable_test.sh
    $ echo 'exit 0' >> /tmp/executable_test.sh
    $ chmod +x /tmp/executable_test.sh

Notice that the file is given executable permissions, which is a
requirement for Avocado to treat it as a executable test. Also notice
that the script exits with status code 0, which signals a successful
result to Avocado.
