#!/usr/bin/env python
"""
Unit tests for Manipulator classes in libvirt_xml module.
"""
import unittest

import common
from virsh_unittest import FakeVirshFactory
from autotest.client.utils import CmdResult
from libvirt_xml.network_xml import NetworkXML
from staging.backports import itertools

# The output of virsh.net_list with only default net
_DEFAULT_NET = (' Name                 State      Autostart     Persistent\n'
                '----------------------------------------------------------\n'
                ' default              active     yes           yes\n')

# Set initial state of test net
global _net_state
_net_state = {'active': False,
              'autostart': False,
              'persistent': False}


class NetworkTestBase(unittest.TestCase):

    """
    Base class for NetworkXML test providing fake virsh commands.
    """

    @staticmethod
    def _net_list(option='--all', **dargs):
        """Bogus net_list command"""
        cmd = 'virsh net-list --all'
        if not _net_state['active'] and not _net_state['persistent']:
            test_net = ''
        else:
            if _net_state['active']:
                active = 'active'
            else:
                active = 'inactive'

            if _net_state['persistent']:
                persistent = 'yes'
            else:
                persistent = 'no'

            if _net_state['autostart']:
                autostart = 'yes'
            else:
                autostart = 'no'

            test_net = ' %-21s%-11s%-14s%-11s\n' % (
                'unittest', active, autostart, persistent)
        output = _DEFAULT_NET + test_net
        return CmdResult(cmd, output)

    @staticmethod
    def _net_define(xmlfile='unittest.xml', **dargs):
        """Bogus net_define command"""
        _net_state['persistent'] = True

    @staticmethod
    def _net_undefine(name='unittest', **dargs):
        """Bogus net_undefine command"""
        _net_state['persistent'] = False
        _net_state['autostart'] = False

    @staticmethod
    def _net_start(name='unittest', **dargs):
        """Bogus net_start command"""
        _net_state['active'] = True

    @staticmethod
    def _net_destroy(name='unittest', **dargs):
        """Bogus net_destroy command"""
        _net_state['active'] = False

    @staticmethod
    def _net_autostart(name='unittest', extra='', **dargs):
        """Bogus net_autostart command"""
        if _net_state['persistent']:
            if extra == '--disable':
                _net_state['autostart'] = False
            else:
                _net_state['autostart'] = True
        else:
            _net_state['autostart'] = False

    def setUp(self):
        # Use defined virsh methods below
        self.bogus_virsh = FakeVirshFactory(preserve=['net_state_dict'])
        self.bogus_virsh.__super_set__('net_list', self._net_list)
        self.bogus_virsh.__super_set__('net_define', self._net_define)
        self.bogus_virsh.__super_set__('net_undefine', self._net_undefine)
        self.bogus_virsh.__super_set__('net_start', self._net_start)
        self.bogus_virsh.__super_set__('net_destroy', self._net_destroy)
        self.bogus_virsh.__super_set__('net_autostart', self._net_autostart)


class NetworkXMLTest(NetworkTestBase):

    """
    Unit test class for manipulator methods in NetworkXML class.
    """

    def test_sync_and_state_dict(self):
        """
        Unit test for sync and state_dict methods of NetworkXML class.

        Traverse all possible state and call sync using the state.
        """

        # Test sync without state option
        test_xml = NetworkXML(network_name='unittest',
                              virsh_instance=self.bogus_virsh)
        test_xml.sync()
        new_state = test_xml.state_dict()
        state = {'active': True,
                 'persistent': True,
                 'autostart': True}
        self.assertEqual(state, new_state)

        for values in itertools.product([True, False], repeat=3):
            # Change network to all possible states.
            keys = ['active', 'persistent', 'autostart']
            state = dict(zip(keys, values))
            test_xml.sync(state=state)

            # Check result's validity.
            new_state = test_xml.state_dict()
            # Transient network can't set autostart
            if state == {'active': True,
                         'persistent': False,
                         'autostart': True}:
                state = {'active': True,
                         'persistent': False,
                         'autostart': False}
            # Non-exist network should return None when retieving state.
            if not state['active'] and not state['persistent']:
                assert new_state is None
            else:
                self.assertEqual(state, new_state)

if __name__ == '__main__':
    unittest.main()
