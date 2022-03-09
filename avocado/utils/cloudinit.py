# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2018
# Author: Cleber Rosa <crosa@redhat.com>

"""
cloudinit configuration support

This module can be easily used with :mod:`avocado.utils.vmimage`,
to configure operating system images via the cloudinit tooling.

Please, keep in mind that if you would like to create/write in ISO images, you
need pycdlib module installed in your environment.

:see: http://cloudinit.readthedocs.io.
"""
import warnings
from http.server import BaseHTTPRequestHandler, HTTPServer

from avocado.utils import astring, iso9660

#: The meta-data file template
#:
#: Positional template variables are: instance-id, hostname
METADATA_TEMPLATE = """instance-id: {0}
hostname: {1}
"""

#: The header expected to be found at the beginning of the user-data file
USERDATA_HEADER = "#cloud-config"

#: A username configuration as per cloudinit/config/cc_set_passwords.py
#:
#: Positional template variables : username
USERNAME_TEMPLATE = """
ssh_pwauth: True

system_info:
   default_user:
      name: {0}
"""

#: A username configuration as per cloudinit/config/cc_set_passwords.py
#:
#: Positional template variables are: password
PASSWORD_TEMPLATE = """
password: {0}
chpasswd:
    expire: False
"""

#: An authorized key configuration for the default user
#:
#: Positional template variables are: ssh_authorized_keys
AUTHORIZED_KEY_TEMPLATE = """
ssh_authorized_keys:
  - {0}
"""

#: A phone home configuration that will post just the instance id
#:
#: Positional template variables are: address, port
PHONE_HOME_TEMPLATE = """
phone_home:
    url: http://{0}:{1}/$INSTANCE_ID/
    post: [ instance_id ]
"""


def iso(output_path, instance_id, username=None, password=None,
        phone_home_host=None, phone_home_port=None, authorized_key=None):
    """
    Generates an ISO image with cloudinit configuration

    The content always include the cloudinit metadata, and optionally
    the userdata content.  On the userdata file, it may contain a
    username/password section (if both parameters are given) and/or a
    phone home section (if both host and port are given).

    :param output_path: the location of the resulting (to be created) ISO
                        image containing the cloudinit configuration
    :param instance_id: the ID of the cloud instance, a form of identification
                        for the dynamically created executing instances
    :param username: the username to be used when logging interactively on the
                     instance
    :param password: the password to be used along with username when
                     authenticating with the login services on the instance
    :param phone_home_host: the address of the host the instance
                            should contact once it has finished
                            booting
    :param phone_home_port: the port acting as an HTTP phone home
                            server that the instance should contact
                            once it has finished booting
    :param authorized_key: a SSH public key to be added as an authorized key
                           for the default user, similar to "ssh-rsa ..."
    :type authorized_key: str
    :raises: RuntimeError if the system can not create ISO images.  On such
             a case, user is expected to install supporting packages, such as
             pycdlib.
    """
    # The only supported method to create/write in an ISO today is via pycdlib
    out = iso9660.iso9660(output_path, ["create", "write"])
    if out is None:
        msg = ("The system lacks support for creating ISO images. ",
               "Please install pycdlib dependency and run again.")
        raise RuntimeError(msg)
    out.create(flags={"interchange_level": 3, "joliet": 3, "vol_ident": 'cidata'})
    metadata = METADATA_TEMPLATE.format(instance_id,
                                        instance_id).encode(astring.ENCODING)
    out.write("/meta-data", metadata)
    userdata = USERDATA_HEADER
    if username:
        userdata += USERNAME_TEMPLATE.format(username)
        if username == "root":
            userdata += "\ndisable_root: False\n"
        if password:
            userdata += PASSWORD_TEMPLATE.format(password)
        if authorized_key:
            userdata += AUTHORIZED_KEY_TEMPLATE.format(authorized_key)
    if phone_home_host and phone_home_port:
        userdata += PHONE_HOME_TEMPLATE.format(phone_home_host, phone_home_port)
    out.write("/user-data", userdata.encode(astring.ENCODING))
    out.close()


class PhoneHomeServerHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests to the phone home server."""

    def do_POST(self):
        """Handles an HTTP POST request.

        Respond with status 200 if the instance phoned back.
        """
        path = self.path[1:]
        if path[-1] == '/':
            path = path[:-1]
        if path == self.server.instance_id:
            self.server.instance_phoned_back = True
        self.send_response(200)

    def log_message(self, format_, *args):  # pylint: disable=W0221
        """Logs an arbitrary message.

        :note: It currently disables any message logging.
        """


class PhoneHomeServer(HTTPServer):
    """Implements the phone home HTTP server.

    Wait the phone home from a given instance.
    """

    def __init__(self, address, instance_id):
        """Initialize the server.

        :param address: a hostname or IP address and port, in the same format
                        given to socket and other servers
        :type address: tuple
        :param instance_id: the identification for the instance that should be
                            calling back, and the condition for the wait to end
        :type instance_id: str
        """
        HTTPServer.__init__(self, address, PhoneHomeServerHandler)
        self.instance_id = instance_id
        self.instance_phoned_back = False

    def wait_for_phone_home(self, new_call=False):
        """Waits for this instance to call.

        :param new_call: Default is False, so if this instance was called back
                         already, this method will return immediately and will
                         not wait for a new call.
        :type new_call: bool
        """
        if new_call:
            self.instance_phoned_back = False

        while not self.instance_phoned_back:
            self.handle_request()

    @classmethod
    def set_up_and_wait_for_phone_home(cls, address, instance_id):
        """
        Sets up a phone home server and waits for the given instance to call

        This is a shorthand for setting up a server that will keep handling
        requests, until it has heard from the specific instance requested.

        :param address: a hostname or IP address and port, in the same format
                        given to socket and other servers
        :type address: tuple
        :param instance_id: the identification for the instance that should be
                            calling back, and the condition for the wait to end
        :type instance_id: str
        """
        s = cls(address, instance_id)
        s.wait_for_phone_home()


def wait_for_phone_home(address, instance_id):
    """
    This method is deprecated.

    Please use :meth:`.PhoneHomeServer.set_up_and_wait_for_phone_home`.
    """
    warnings.warn(("wait_for_phone_home is deprecated. Please use "
                   "PhoneHomeServer.set_up_and_wait_for_phone_home()"),
                  DeprecationWarning)
    PhoneHomeServer.set_up_and_wait_for_phone_home(address, instance_id)
