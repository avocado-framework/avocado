# Copyright: Red Hat Inc. 2015
# Author: Cleber Rosa <cleber@redhat.com>

from avocado.core.restclient import connection

c = connection.get_default()
print(c.request("version"))
