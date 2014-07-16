"""
Classes to support XML for serial devices

http://libvirt.org/formatdomain.html#elementCharSerial
"""

from virttest.libvirt_xml import base, accessors
from virttest.libvirt_xml.devices.character import CharacterBase


class Serial(CharacterBase):

    __slots__ = ('protocol_type',)

    def __init__(self, type_name='pty', virsh_instance=base.virsh):
        # Additional attribute for protocol type (raw, telnet, telnets, tls)
        accessors.XMLAttribute('protocol_type', self, parent_xpath='/',
                               tag_name='protocol', attribute='type')
        super(Serial, self).__init__(device_tag='serial', type_name=type_name,
                                     virsh_instance=virsh_instance)
