# Copyright: Red Hat Inc. 2015
# Author: Cleber Rosa <cleber@redhat.com>

from avocado.restclient import connection
from avocado.restclient import response

c = connection.get_default()
print(c.get_api_list())
