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
Module to provide classes for Virtual Machines.
"""

import logging
import subprocess
import xml.etree.cElementTree as etree
from xml.dom import minidom

from . import remoter

LOG = logging.getLogger('avocado.test')

try:
    import libvirt
except ImportError:
    VIRT_CAPABLE = False
    LOG.info('Virt module is disabled: could not import libvirt')
else:
    VIRT_CAPABLE = True


if remoter.REMOTE_CAPABLE is False:
    VIRT_CAPABLE = False
    LOG.info('Virt module is disabled: remote module is disabled')


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

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__,
                           self.uri)

    @property
    def domains(self):
        """
        Property to get the list of all domains.

        :return: a list of instances of :class:`libvirt.virDomain`.
        """
        return self.connection.listAllDomains()

    def connect(self):
        """
        Connect to the hypervisor.
        """
        if self.connected is False:
            try:
                self.connection = libvirt.open(self.uri)
            except libvirt.libvirtError:
                self.connected = False
                return None
            else:
                self.connected = True
        return self.connection

    def find_domain_by_name(self, name):
        """
        Find domain by name.

        :param domain: the domain name.
        :return: an instance of :class:`libvirt.virDomain`.
        """
        for domain in self.domains:
            if name == domain.name():
                return domain
        return None


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

    @property
    def is_active(self):
        """
        Property to check if VM is active.

        :return: if VM is active.
        :rtype: Boolean
        """
        return bool(self.domain.isActive())

    @property
    def name(self):
        """
        Property with the name of VM.

        :return: the name of VM.
        """
        return self.domain.name()

    @property
    def state(self):
        """
        Property with the state of VM.

        :return: current state name.
        """
        states = ['No state',
                  'Running',
                  'Blocked',
                  'Paused',
                  'Shutting down',
                  'Shutoff',
                  'Crashed']
        return states[self.domain.info()[0]]

    def start(self):
        """
        Start VM.
        """
        if self.is_active is False:
            self.domain.create()

    def suspend(self):
        """
        Suspend VM.
        """
        if self.is_active:
            self.domain.suspend()

    def resume(self):
        """
        Resume VM.
        """
        if self.is_active:
            self.domain.resume()

    def reboot(self):
        """
        Reboot VM.
        """
        if self.is_active:
            self.domain.reboot()

    def shutdown(self):
        """
        Shutdown VM.
        """
        if self.is_active:
            self.domain.shutdown()

    def reset(self):
        """
        Reset VM.
        """
        if self.is_active:
            self.domain.reset()

    def stop(self):
        """
        Stop VM.
        """
        if self.is_active:
            self.domain.destroy()

    def _system_checkpoint_xml(self, name=None, description=None):
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

    @property
    def snapshots(self):
        return self.domain.snapshotListNames()

    def create_snapshot(self, name=None):
        """
        Creates a snapshot of kind 'system checkpoint'.
        """
        xml = self._system_checkpoint_xml(name)
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
            self.remote = remoter.Remote(hostname, username, password)
            res = self.remote.uptime()
            if res.succeeded:
                self.logged = True
        else:
            self.logged = False

    def ip_address(self):
        """
        Returns the IP address associated with the MAC address of this VM

        Inspired from:
        https://raw.githubusercontent.com/mcepl/virt-addr/master/virt-addr.py

        :returns: either the IP address or None if not found
        :rtype: str or None
        """
        desc = etree.fromstring(self.domain.XMLDesc(0))
        mac_path = "devices/interface[@type='network']/mac"
        node = desc.find(mac_path)
        if node is None:
            return None

        mac = node.get("address")
        if mac is None:
            return None

        mac = mac.lower().strip()
        output = subprocess.Popen(["arp", "-n"],
                                  stdout=subprocess.PIPE).communicate()[0]
        lines = [line.split() for line in output.split("\n")[1:]]
        addresses = [line[0] for line in lines if (line and (line[2] == mac))]
        if addresses:
            # Just return the first address, this is a best effort attempt
            return addresses[0]


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
