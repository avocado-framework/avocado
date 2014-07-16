"""
Address device / device descriptor class

http://libvirt.org/formatdomain.html#elementsAddress
"""

from virttest.libvirt_xml import accessors, xcepts
from virttest.libvirt_xml.devices import base


class Address(base.TypedDeviceBase):

    __slots__ = ('attrs',)

    def __init__(self, type_name, virsh_instance=base.base.virsh):
        # Blindly accept any/all attributes as simple dictionary
        accessors.XMLElementDict('attrs', self, parent_xpath='/',
                                 tag_name='address')
        super(self.__class__, self).__init__(device_tag='address',
                                             type_name=type_name,
                                             virsh_instance=virsh_instance)

    @classmethod
    def new_from_dict(cls, attributes, virsh_instance=base.base.virsh):
        # type_name is manditory, throw exception if doesn't exist
        try:
            # pop() so don't process again in loop below
            instance = cls(type_name=attributes.pop('type_name'),
                           virsh_instance=virsh_instance)
        except (KeyError, AttributeError):
            raise xcepts.LibvirtXMLError("type_name is manditory for "
                                         "Address class")
        # Stick property values in as attributes
        xtfroot = instance.xmltreefile.getroot()
        for key, value in attributes.items():
            xtfroot.set(key, value)
        return instance

    @classmethod
    def new_from_element(cls, element, virsh_instance=base.base.virsh):
        # element uses type attribute, class uses type_name
        edict = dict(element.items())
        try:
            edict['type_name'] = edict.pop('type')
        except (KeyError, AttributeError):
            raise xcepts.LibvirtXMLError("type attribute is manditory for "
                                         "Address class")
        return cls.new_from_dict(edict, virsh_instance=virsh_instance)
