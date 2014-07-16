"""
interface device support class(es)

http://libvirt.org/formatdomain.html#elementsNICS
"""

from virttest.libvirt_xml import accessors
from virttest.libvirt_xml.devices import base, librarian


class Interface(base.TypedDeviceBase):

    __slots__ = ('source', 'mac_address', 'bandwidth_inbound',
                 'bandwidth_outbound', 'portgroup', 'model',
                 'driver', 'address')

    def __init__(self, type_name, virsh_instance=base.base.virsh):
        super(Interface, self).__init__(device_tag='interface',
                                        type_name=type_name,
                                        virsh_instance=virsh_instance)
        accessors.XMLElementDict(property_name="source",
                                 libvirtxml=self,
                                 forbidden=None,
                                 parent_xpath='/',
                                 tag_name='source')
        accessors.XMLElementDict(property_name="driver",
                                 libvirtxml=self,
                                 forbidden=None,
                                 parent_xpath='/',
                                 tag_name='driver')
        accessors.XMLAttribute(property_name="mac_address",
                               libvirtxml=self,
                               forbidden=None,
                               parent_xpath='/',
                               tag_name='mac',
                               attribute='address')
        accessors.XMLElementDict(property_name="bandwidth_inbound",
                                 libvirtxml=self,
                                 forbidden=None,
                                 parent_xpath='/bandwidth',
                                 tag_name='inbound')
        accessors.XMLElementDict(property_name="bandwidth_outbound",
                                 libvirtxml=self,
                                 forbidden=None,
                                 parent_xpath='/bandwidth',
                                 tag_name='outbound')
        accessors.XMLAttribute(property_name="portgroup",
                               libvirtxml=self,
                               forbidden=None,
                               parent_xpath='/',
                               tag_name='source',
                               attribute='portgroup')
        accessors.XMLAttribute(property_name="model",
                               libvirtxml=self,
                               forbidden=None,
                               parent_xpath='/',
                               tag_name='model',
                               attribute='type')
        accessors.XMLElementNest('address', self, parent_xpath='/',
                                 tag_name='address', subclass=self.Address,
                                 subclass_dargs={'type_name': 'drive',
                                                 'virsh_instance': virsh_instance})
    # For convenience
    Address = librarian.get('address')
