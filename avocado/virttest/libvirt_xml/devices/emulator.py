"""
Support for the pseudo 'emulator' device XML

http://libvirt.org/formatdomain.html#elementsDevices
"""

from virttest.libvirt_xml import accessors
from virttest.libvirt_xml.devices import base


class Emulator(base.UntypedDeviceBase):

    __slots__ = ('path',)

    def __init__(self, virsh_instance=base.base.virsh):
        accessors.XMLElementText('path', self, parent_xpath='/',
                                 tag_name='emulator')
        super(Emulator, self).__init__(device_tag='emulator',
                                       virsh_instance=virsh_instance)
