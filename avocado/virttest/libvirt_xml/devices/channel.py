"""
Classes to support XML for channel devices

http://libvirt.org/formatdomain.html#elementCharSerial
"""

from virttest.libvirt_xml import base
from virttest.libvirt_xml.devices.character import CharacterBase


class Channel(CharacterBase):

    __slots__ = []

    def __init__(self, type_name='unix', virsh_instance=base.virsh):
        super(
            Channel, self).__init__(device_tag='channel', type_name=type_name,
                                    virsh_instance=virsh_instance)
