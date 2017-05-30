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
# Copyright: Red Hat Inc. 2014-2017
# Authors: Ruda Moura <rmoura@redhat.com>
#          Cleber Rosa <crosa@redhat.com>

import getpass
import logging
import sys
import time
from xml.dom import minidom

import libvirt

from avocado.core import exit_codes, exceptions
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLI
from avocado_runner_remote import Remote, RemoteTestRunner


class VirtError(Exception):

    """
    Generic exception class to propagate underling
    errors to the caller.
    """
    pass


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
                libvirt.registerErrorHandler(self.handler, 'context')
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

    @staticmethod
    def handler(ctxt, err):
        """
        This overwrites the libvirt default error handler, in order to
        avoid unwanted messages from libvirt exceptions to be sent for
        stdout.
        """
        pass


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
            self.remote = Remote(hostname, username, password)
            res = self.remote.uptime()
            if res.succeeded:
                self.logged = True
        else:
            self.logged = False

    def ip_address(self, timeout=30):
        """
        Returns the domain IP address consulting qemu-guest-agent
        through libvirt.

        :returns: either the IP address or None if not found
        :rtype: str or None
        """
        timelimit = time.time() + timeout
        while True:
            try:
                ip = self._get_ip_from_libvirt_agent()
                if ip is not None:
                    return ip
            except libvirt.libvirtError as exception:
                # Qemu guest agent takes time to be ready, but
                # libvirt raises an exception here if it's not.
                # Let's be nice and wait for the guest agent, if
                # that's the problem.
                errno = libvirt.VIR_ERR_AGENT_UNRESPONSIVE
                if exception.get_error_code() == errno:
                    pass
                else:
                    return None

            if time.time() > timelimit:
                return None
            time.sleep(1)

    def _get_ip_from_libvirt_agent(self):
        """
        Retrieves from libvirt/qemu-guest-agent the first IPv4
        non-loopback IP from the first non-loopback device.

        Libvirt response example:
        {'ens3': {'addrs': [{'addr': '192.168.122.4',
                             'prefix': 24,
                             'type': 0},
                            {'addr': 'fe80::5054:ff:fe0c:9c9b',
                             'prefix': 64,
                             'type': 1}],
                  'hwaddr': '52:54:00:0c:9c:9b'},
           'lo': {'addrs': [{'addr': '127.0.0.1',
                             'prefix': 8,
                             'type': 0},
                            {'addr': '::1',
                             'prefix': 128,
                             'type': 1}],
                  'hwaddr': '00:00:00:00:00:00'}}

        :return: either the IP address or None if not found.
        """
        querytype = libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT
        ipversion = libvirt.VIR_IP_ADDR_TYPE_IPV4

        ifaces = self.domain.interfaceAddresses(querytype)
        for iface, data in ifaces.iteritems():
            if data['addrs'] and data['hwaddr'] != '00:00:00:00:00:00':
                ip_addr = data['addrs'][0]['addr']
                ip_type = data['addrs'][0]['type']
                if ip_type == ipversion and not ip_addr.startswith('127.'):
                    return ip_addr
        return None


def vm_connect(domain_name, hypervisor_uri='qemu:///system'):
    """
    Connect to a Virtual Machine.

    :param domain_name: the domain name.
    :param hypervisor_uri: the hypervisor connection URI.
    :return: an instance of :class:`VM`
    """
    hyper = Hypervisor(hypervisor_uri)
    if hyper.connect() is None:
        raise VirtError('Cannot connect to hypervisor at "%s"' %
                        hypervisor_uri)

    dom = hyper.find_domain_by_name(domain_name)
    if dom is None:
        raise VirtError('Domain "%s" could not be found' %
                        domain_name)

    return VM(hyper, dom)


class VMTestRunner(RemoteTestRunner):

    """
    Test runner to run tests using libvirt domain
    """

    def __init__(self, job, result):
        super(VMTestRunner, self).__init__(job, result)
        #: VM used during testing
        self.vm = None

    def setup(self):
        """
        Initialize VM and establish connection
        """
        # Super called after VM is found and initialized
        stdout_claimed_by = getattr(self.job.args, 'stdout_claimed_by', None)
        if not stdout_claimed_by:
            self.job.log.info("DOMAIN     : %s", self.job.args.vm_domain)
        try:
            self.vm = vm_connect(self.job.args.vm_domain,
                                 self.job.args.vm_hypervisor_uri)
        except VirtError as exception:
            raise exceptions.JobError(exception.message)
        if self.vm.start() is False:
            e_msg = "Could not start VM '%s'" % self.job.args.vm_domain
            raise exceptions.JobError(e_msg)
        assert self.vm.domain.isActive() is not False
        # If hostname wasn't given, let's try to find out the IP address
        if self.job.args.vm_hostname is None:
            self.job.args.vm_hostname = self.vm.ip_address()
            if self.job.args.vm_hostname is None:
                e_msg = ("Could not find the IP address for VM '%s'. Please "
                         "set it explicitly with --vm-hostname" %
                         self.job.args.vm_domain)
                raise exceptions.JobError(e_msg)
        if self.job.args.vm_cleanup is True:
            self.vm.create_snapshot()
            if self.vm.snapshot is None:
                e_msg = ("Could not create snapshot on VM '%s'" %
                         self.job.args.vm_domain)
                raise exceptions.JobError(e_msg)
        # Finish remote setup and copy the tests
        self.job.args.remote_hostname = self.job.args.vm_hostname
        self.job.args.remote_port = self.job.args.vm_port
        self.job.args.remote_username = self.job.args.vm_username
        self.job.args.remote_password = self.job.args.vm_password
        self.job.args.remote_key_file = self.job.args.vm_key_file
        self.job.args.remote_timeout = self.job.args.vm_timeout
        super(VMTestRunner, self).setup()

    def tear_down(self):
        """
        Stop VM and restore snapshot (if asked for it)
        """
        super(VMTestRunner, self).tear_down()
        if (self.job.args.vm_cleanup is True and
                isinstance(getattr(self, 'vm', None), VM)):
            self.vm.stop()
            if self.vm.snapshot is not None:
                self.vm.restore_snapshot()
            self.vm = None


class VMCLI(CLI):

    """
    Run tests on a Virtual Machine
    """

    name = 'vm'
    description = "Virtual Machine options for 'run' subcommand"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        msg = 'test execution on a Virtual Machine'
        vm_parser = run_subcommand_parser.add_argument_group(msg)
        vm_parser.add_argument('--vm-domain',
                               help=('Specify Libvirt Domain Name'))
        vm_parser.add_argument('--vm-hypervisor-uri',
                               default='qemu:///system',
                               help=('Specify hypervisor URI driver '
                                     'connection. Current: %(default)s'))
        vm_parser.add_argument('--vm-hostname', default=None,
                               help=('Specify VM hostname to login. By '
                                     'default Avocado attempts to '
                                     'automatically find the VM IP '
                                     'address.'))
        vm_parser.add_argument('--vm-port', dest='vm_port',
                               default=22, type=int,
                               help=('Specify the SSH port number to login on '
                                     'VM. Default: %(default)s'))
        vm_parser.add_argument('--vm-username', default=getpass.getuser(),
                               help=('Specify the username to login on VM. '
                                     'Default: %(default)s'))
        vm_parser.add_argument('--vm-password',
                               default=None,
                               help='Specify the password to login on VM')
        vm_parser.add_argument('--vm-key-file',
                               dest='vm_key_file', default=None,
                               help=('Specify an identity file with '
                                     'a private key instead of a password '
                                     '(Example: .pem files from Amazon EC2)'))
        vm_parser.add_argument('--vm-cleanup',
                               action='store_true', default=False,
                               help=('Restore VM to a previous state, '
                                     'before running tests'))
        vm_parser.add_argument('--vm-timeout', metavar='SECONDS',
                               default=120, type=int,
                               help=("Amount of time (in seconds) to "
                                     "wait for a successful connection"
                                     " to the virtual machine. Defaults"
                                     " to %(default)s seconds."))

    @staticmethod
    def _check_required_args(args, enable_arg, required_args):
        """
        :return: True when enable_arg enabled and all required args are set
        :raise sys.exit: When missing required argument.
        """
        if (not hasattr(args, enable_arg) or
                not getattr(args, enable_arg)):
            return False
        missing = []
        for arg in required_args:
            if not getattr(args, arg):
                missing.append(arg)
        if missing:
            LOG_UI.error("Use of %s requires %s arguments to be set. Please "
                         "set %s.", enable_arg, ', '.join(required_args),
                         ', '.join(missing))

            return sys.exit(exit_codes.AVOCADO_FAIL)
        return True

    def run(self, args):
        if self._check_required_args(args, 'vm_domain', ('vm_domain',)):
            args.test_runner = VMTestRunner
