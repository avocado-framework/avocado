"""
Parallel device support class(es)

http://libvirt.org/formatdomain.html#elementCharSerial
"""

from virttest.libvirt_xml import base
from virttest.libvirt_xml.devices.character import CharacterBase


class Parallel(CharacterBase):

    __slots__ = []

    def __init__(self, type_name='pty', virsh_instance=base.virsh):
        super(Parallel, self).__init__(device_tag='parallel',
                                       type_name=type_name,
                                       virsh_instance=virsh_instance)
