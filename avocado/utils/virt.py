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
# Copyright: Red Hat Inc. 2014
# Author: Ruda Moura <rmoura@redhat.com>

"""
Module to provide classes for virtualization.
"""

import libvirt

from xml.dom import minidom
from avocado.utils import remote


class Hypervisor(object):

    """
    The Hypervisor connection class.
    """

    def __init__(self, uri=None):
        """
        Creates an instance of class Hypervisor.

        :param uri: the connection URI.
        """
        self.uri = uri
        self.connection = None
        self.connected = False
        self.domains = []

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__,
                           self.uri)

    def _get_domains(self):
        self.domains = self.connection.listAllDomains()

    def connect(self):
        """
        Connect to the hypervisor.
        """
        if self.connected is False:
            try:
                self.connection = libvirt.open(self.uri)
            except libvirt.libvirtError as err:
                self.connected = False
                return None
            else:
                self.connected = True
        self._get_domains()
        return self.connection

    def find_domain_by_name(self, name):
        """
        Find domain by name.

        :param domain: the domain name.
        :return: an instance of :class:`libvirt.virDomain`.
        """
        self._get_domains()
        for domain in self.domains:
            if name == domain.name():
                return domain
        return None

    def start_domain(self, xml):
        """
        Start domain.
        :param xml: the XML description.
        :return: an instance of :class:`libvirt.virDomain`.
        """
        dom = None
        try:
            dom = self.connection.createXML(xml)
        except libvirt.libvirtError:
            pass
        return dom


class VM(object):

    """
    The Virtual Machine handler class.
    """

    def __init__(self, hypervisor, domain):
        """
        Creates an instance of VM class.

        :param hypervisor: an instance of :class:`Hypervisor`.
        :param domain: an instance of :class:`libvirt.virDomain`.
        """
        self.hypervisor = hypervisor
        self.domain = domain
        self.logged = False
        self.snapshot = None

    def __str__(self):
        return "%s('%s', '%s')" % (self.__class__.__name__,
                                   self.hypervisor.uri,
                                   self.domain.name())

    def start(self):
        """
        Start VM.
        """
        if self.domain.isActive():
            return True
        xml = self.domain.XMLDesc()
        dom = self.hypervisor.start_domain(xml)
        if dom:
            self.domain = dom
            return True
        else:
            return False

    def _create_snapshot_xml(self, name=None, description=None):
        def create_element(doc, tag, text):
            el = doc.createElement(tag)
            txt = doc.createTextNode(text)
            el.appendChild(txt)
            return el
        doc = minidom.Document()
        root = doc.createElement('domainsnapshot')
        doc.appendChild(root)
        if name is not None:
            root.appendChild(create_element(doc, 'name', name))
        if description is None:
            description = 'Avocado Test Runner'
        root.appendChild(create_element(doc, 'description', description))
        return doc.toxml()

    def create_snapshot(self, name=None):
        """
        Create a snapshot point.
        """
        xml = self._create_snapshot_xml(name)
        self.snapshot = self.domain.snapshotCreateXML(xml)
        return self.snapshot

    def revert_snapshot(self):
        """
        Revert to previous snapshot.
        """
        if self.snapshot is not None:
            self.domain.revertToSnapshot(self.snapshot)

    def delete_snapshot(self):
        """
        Delete the current snapshot.
        """
        if self.snapshot is not None:
            self.snapshot.delete()
            self.snapshot = None

    def restore_snapshot(self):
        """
        Revert to previous snapshot and delete the snapshot point.
        """
        self.revert_snapshot()
        self.delete_snapshot()

    def setup_login(self, hostname, username, password=None):
        """
        Setup login on VM.

        :param hostname: the hostname.
        :param username: the username.
        :param password: the password.
        """
        if not self.logged:
            self.remote = self.remote.Remote(hostname, username, password)
            res = self.remote.uptime()
            if res.succeeded:
                self.logged = True
        else:
            self.logged = False


def vm_connect(domain_name, hypervisor_uri='qemu:///system'):
    """
    Connect to a Virtual Machine.

    :param domain_name: the domain name.
    :param hypervisor_uri: the hypervisor connection URI.
    :return: an instance of :class:`VM`
    """
    hyper = Hypervisor(hypervisor_uri)
    hyper.connect()
    dom = hyper.find_domain_by_name(domain_name)
    vm = VM(hyper, dom)
    return vm
