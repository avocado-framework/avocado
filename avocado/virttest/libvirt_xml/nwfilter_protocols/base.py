"""
Common base classes for filter rule protocols
"""

import logging
from StringIO import StringIO
from virttest import xml_utils
from virttest.libvirt_xml import base, xcepts, accessors


class UntypedDeviceBase(base.LibvirtXMLBase):

    """
    Base class implementing common functions for all rule protocol XML w/o a
    type attr.
    """

    __slots__ = ('protocol_tag',)

    # Subclasses are expected to hide protocol_tag
    def __init__(self, protocol_tag, virsh_instance=base.virsh):
        """
        Initialize untyped filter rule instance's basic XML with protocol_tag
        """
        super(UntypedDeviceBase, self).__init__(virsh_instance=virsh_instance)
        # Just a regular dictionary value
        # (Using a property to change element tag won't work)
        self['protocol_tag'] = protocol_tag
        # setup bare-bones XML
        self.xml = u"<%s/>" % protocol_tag

    def from_element(self, element):
        """
        Stateful component to helper method for new_from_element.
        """
        class_name = self.__class__.__name__
        if element.tag != class_name.lower():
            raise xcepts.LibvirtXMLError('Refusing to create %s instance'
                                         'from %s tagged element'
                                         % (class_name, element.tag))
        # XMLTreeFile only supports element trees
        etree = xml_utils.ElementTree.ElementTree(element)
        # ET only writes to open file-like objects
        xmlstr = StringIO()
        # Need element tree string value to initialize LibvirtXMLBase.xml
        etree.write(xmlstr, xml_utils.ENCODING)
        # Create a new XMLTreeFile object based on string input
        self.xml = xmlstr.getvalue()

    @classmethod
    def new_from_element(cls, element, virsh_instance=base.virsh):
        """
        Create a new filter rule XML instance from an single ElementTree
        element
        """
        # subclasses __init__ only takes virsh_instance parameter
        instance = cls(virsh_instance=virsh_instance)
        instance.from_element(element)
        return instance

    @classmethod
    def new_from_dict(cls, properties, virsh_instance=base.virsh):
        """
        Create a new filter rule XML instance from a dict-like object
        """
        instance = cls(virsh_instance=virsh_instance)
        for key, value in properties.items():
            setattr(instance, key, value)
        return instance


class TypedDeviceBase(UntypedDeviceBase):

    """
    Base class implementing common functions for all filter rule XML w/o a
    type attr.
    """

    __slots__ = ('type_name',)

    # Subclasses are expected to hide protocol_tag
    def __init__(self, protocol_tag, type_name, virsh_instance=base.virsh):
        """
        Initialize Typed filter rule protocol instance's basic XML with
        type_name & protocol_tag
        """
        # generate getter, setter, deleter for 'type_name' property
        accessors.XMLAttribute('type_name', self,
                               # each rule protocol is it's own XML "document"
                               # because python 2.6 ElementPath is broken
                               parent_xpath='/',
                               tag_name=protocol_tag,
                               attribute='type')
        super(TypedDeviceBase, self).__init__(protocol_tag=protocol_tag,
                                              virsh_instance=virsh_instance)
        # Calls accessor to modify xml
        self.type_name = type_name

    @classmethod
    def new_from_element(cls, element, virsh_instance=base.virsh):
        """
        Hides type_name from superclass new_from_element().
        """
        type_name = element.get('type', None)
        # subclasses must hide protocol_tag parameter
        instance = cls(type_name=type_name,
                       virsh_instance=virsh_instance)
        instance.from_element(element)
        return instance
