"""
Console device support class(es)

http://libvirt.org/formatdomain.html#elementCharSerial
"""

from virttest.libvirt_xml import base
from virttest.libvirt_xml.devices.character import CharacterBase


class Console(CharacterBase):

    __slots__ = []

    def __init__(self, type_name='pty', virsh_instance=base.virsh):
        super(
            Console, self).__init__(device_tag='console', type_name=type_name,
                                    virsh_instance=virsh_instance)
