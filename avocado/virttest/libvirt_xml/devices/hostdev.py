"""
hostdev device support class(es)

http://libvirt.org/formatdomain.html#elementsHostDev
"""

from virttest.libvirt_xml.devices import base
from virttest.libvirt_xml import accessors


class Hostdev(base.TypedDeviceBase):

    __slots__ = ('mode', 'type', 'source_address', 'managed')

    def __init__(self, type_name="hostdev", virsh_instance=base.base.virsh):
        accessors.XMLAttribute('type', self, parent_xpath='/',
                               tag_name='hostdev', attribute='type')
        accessors.XMLAttribute('mode', self, parent_xpath='/',
                               tag_name='hostdev', attribute='mode')
        accessors.XMLAttribute('managed', self, parent_xpath='/',
                               tag_name='hostdev', attribute='managed')
        accessors.XMLElementDict('source_address', self, parent_xpath='/source',
                                 tag_name='address')
        super(self.__class__, self).__init__(device_tag='hostdev',
                                             type_name=type_name,
                                             virsh_instance=virsh_instance)
