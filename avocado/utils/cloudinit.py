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
"""

import io

from six.moves import BaseHTTPServer

# FIXME: should be using avocado.utils.iso9660, with support for creating images
# https://trello.com/c/gZxdS6W6/1386-avocadoutilsiso9660-support-for-creating-images
import pycdlib


#: The meta-data file template
METADATA_TEMPLATE = """instance-id: {0}
hostname: {1}
"""

#: The header expected to be found at the beginning of the user-data file
USERDATA_HEADER = "#cloud-config"

#: A password configuration as per cloudinit/config/cc_set_passwords.py
PASSWORD_TEMPLATE = """
ssh_pwauth: True

system_info:
   default_user:
      name: {0}

password: {1}
chpasswd:
    expire: False
"""

PHONE_HOME_TEMPLATE = """
phone_home:
    url: http://{0}:{1}/$INSTANCE_ID/
    post: [ instance_id ]
"""


def create_empty_iso():
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, joliet=3, vol_ident='cidata')
    return iso


def iso_add_metadata(iso, instance_id):
    metadata = METADATA_TEMPLATE.format(instance_id, instance_id)
    iso.add_fp(io.BytesIO(metadata), len(metadata), '/METADATA;1',
               joliet_path='/meta-data')


def iso_add_userdata(iso, username=None, password=None,
                     phone_home_host=None, phone_home_port=None):
    userdata = USERDATA_HEADER

    if username and password:
        userdata += PASSWORD_TEMPLATE.format(username, password)

    if phone_home_host and phone_home_port:
        userdata += PHONE_HOME_TEMPLATE.format(phone_home_host, phone_home_port)

    iso.add_fp(io.BytesIO(userdata), len(userdata), '/USERDATA;1',
               joliet_path='/user-data')


def generate_iso(output_path, instance_id, username=None, password=None,
                 phone_home_host=None, phone_home_port=None):
    iso = create_empty_iso()

    iso_add_metadata(iso, instance_id)
    iso_add_userdata(iso, username, password, phone_home_host, phone_home_port)

    iso.write(output_path)
    iso.close()


class PhoneHomeServerHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_POST(self):
        path = self.path[1:]
        if path[-1] == '/':
            path = path[:-1]
        if path == self.server.instance_id:
            self.server.instance_phoned_back = True
        self.send_response(200)


class PhoneHomeServer(BaseHTTPServer.HTTPServer):

    def __init__(self, address, instance_id):
        BaseHTTPServer.HTTPServer.__init__(self, address, PhoneHomeServerHandler)
        self.instance_id = instance_id
        self.instance_phoned_back = False


def wait_for_phone_home(address, instance_id):
    s = PhoneHomeServer(address, instance_id)
    while not s.instance_phoned_back:
        s.handle_request()
