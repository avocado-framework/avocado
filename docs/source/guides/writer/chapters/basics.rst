Writing a Simple Test
---------------------

This very simple example of simple test written in shell script::

    $ echo '#!/bin/bash' > /tmp/simple_test.sh
    $ echo 'exit 0' >> /tmp/simple_test.sh
    $ chmod +x /tmp/simple_test.sh

Notice that the file is given executable permissions, which is a requirement for
Avocado to treat it as a simple test. Also notice that the script exits with status
code 0, which signals a successful result to Avocado.
