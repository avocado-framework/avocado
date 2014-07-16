"""
hub device support class(es)

http://libvirt.org/formatdomain.html#elementsHub
"""

from virttest.libvirt_xml import accessors
from virttest.libvirt_xml.devices import base, librarian


class Hub(base.TypedDeviceBase):
    __slots__ = ('address',)

    def __init__(self, type_name, virsh_instance=base.base.virsh):
        super(Hub, self).__init__(device_tag='hub',
                                  type_name=type_name,
                                  virsh_instance=virsh_instance)
        accessors.XMLElementNest('address', self, parent_xpath='/',
                                 tag_name='address', subclass=self.Address,
                                 subclass_dargs={'type_name': 'usb',
                                                 'virsh_instance': virsh_instance})
    # For convenience
    Address = librarian.get('address')

    def new_hub_address(self, type_name='usb', **dargs):
        """
        Return a new hub Address instance and set properties from dargs
        """
        new_one = self.Address(type_name=type_name, virsh_instance=self.virsh)
        for key, value in dargs.items():
            setattr(new_one, key, value)
        return new_one
