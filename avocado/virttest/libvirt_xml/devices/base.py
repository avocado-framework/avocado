"""
Common base classes for devices
"""

import logging
from StringIO import StringIO
from virttest import xml_utils
from virttest.libvirt_xml import base, xcepts, accessors
from virttest.xml_utils import ElementTree


class UntypedDeviceBase(base.LibvirtXMLBase):

    """
    Base class implementing common functions for all device XML w/o a type attr.
    """

    __slots__ = ('device_tag',)

    # Subclasses are expected to hide device_tag
    def __init__(self, device_tag, virsh_instance=base.virsh):
        """
        Initialize untyped device instance's basic XML with device_tag
        """
        super(UntypedDeviceBase, self).__init__(virsh_instance=virsh_instance)
        # Just a regular dictionary value
        # (Using a property to change element tag won't work)
        self['device_tag'] = device_tag
        # setup bare-bones XML
        self.xml = u"<%s/>" % device_tag

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
        Create a new device XML instance from an single ElementTree element
        """
        # subclasses __init__ only takes virsh_instance parameter
        instance = cls(virsh_instance=virsh_instance)
        instance.from_element(element)
        return instance

    @classmethod
    def new_from_dict(cls, properties, virsh_instance=base.virsh):
        """
        Create a new device XML instance from a dict-like object
        """
        instance = cls(virsh_instance=virsh_instance)
        for key, value in properties.items():
            setattr(instance, key, value)
        return instance

    # Add accessors here to be used by any elements
    def _get_list(self, tag_filter):
        """
        Return a list of dictionaries containing element's attributes.
        """
        dict_list = []
        elements = self.xmltreefile.findall(tag_filter)
        for element in elements:
            dict_list.append(dict(element.items()))
        return dict_list

    def _set_list(self, tag_name, value):
        """
        Set all elements to the value list of dictionaries of element's
        attributes.
        """
        xcept = xcepts.LibvirtXMLError("Must set %s child %s elements from"
                                       " a list of dictionary"
                                       % (self.device_tag, tag_name))
        if not isinstance(value, list):
            raise xcept
        # Start with clean slate
        self._del_list(tag_name)
        for dict_item in value:
            if not isinstance(dict_item, dict):
                raise xcept
            ElementTree.SubElement(self.xmltreefile.getroot(),
                                   tag_name, dict_item)
        self.xmltreefile.write()

    def _del_list(self, tag_filter):
        """
        Remove the list of dictionaries containing each element's attributes.
        """
        element = self.xmltreefile.find(tag_filter)
        while element is not None:
            self.xmltreefile.getroot().remove(element)
            element = self.xmltreefile.find(tag_filter)
        self.xmltreefile.write()

    def _add_item(self, prop_name, **attributes):
        """
        Convenience method for appending an element from dictionary of
        attributes.
        """
        items = self[prop_name]  # xml element name
        items.append(attributes)
        self[prop_name] = items

    def _update_item(self, prop_name, index, **attributes):
        """
        Convenience method for merging values into an element's attributes
        """
        items = self[prop_name]  # xml element name
        item = items[index]
        item.update(attributes)
        self[prop_name] = items


class TypedDeviceBase(UntypedDeviceBase):

    """
    Base class implementing common functions for all device XML w/o a type attr.
    """

    __slots__ = ('type_name',)

    # Subclasses are expected to hide device_tag
    def __init__(self, device_tag, type_name, virsh_instance=base.virsh):
        """
        Initialize Typed device instance's basic XML with type_name & device_tag
        """
        # generate getter, setter, deleter for 'type_name' property
        accessors.XMLAttribute('type_name', self,
                               # each device is it's own XML "document"
                               # because python 2.6 ElementPath is broken
                               parent_xpath='/',
                               tag_name=device_tag,
                               attribute='type')
        super(TypedDeviceBase, self).__init__(device_tag=device_tag,
                                              virsh_instance=virsh_instance)
        # Calls accessor to modify xml
        self.type_name = type_name

    @classmethod
    def new_from_element(cls, element, virsh_instance=base.virsh):
        """
        Hides type_name from superclass new_from_element().
        """
        type_name = element.get('type', None)
        # subclasses must hide device_tag parameter
        instance = cls(type_name=type_name,
                       virsh_instance=virsh_instance)
        instance.from_element(element)
        return instance


# Metaclass is a type-of-types or a class-generating class.
# Using it here to avoid copy-pasting very similar class
# definitions into every unwritten device module.
#
# Example usage for stub disk device:
#
# class Disk(base.TypedDeviceBase):
#     __metaclass__ = base.StubDeviceMeta
#     _device_tag = 'disk'
#     _def_type_name = 'block'
#
# will become defined as:
#
# class Disk(base.TypedDeviceBase):
#     def __init__(self, type_name='block', virsh_instance=base.virsh):
#         issue_warning()
#         super(Disk, self).__init__(device_tag='disk'),
#                                    type_name=type_name,
#                                    virsh_instance=virsh_instance)
#

class StubDeviceMeta(type):

    """
    Metaclass for generating stub Device classes where not fully implemented yet
    """

    warning_issued = False

    # mcs is the class object being generated, name is it's name, bases
    # is tuple of all baseclasses, and dct is what will become mcs's
    # __dict__ after super(...).__init__() is called.
    def __init__(mcs, name, bases, dct):
        """
        Configuration for new class
        """

        # Keep pylint happy
        dct = dict(dct)

        # Call type() to setup new class and store it as 'mcs'
        super(StubDeviceMeta, mcs).__init__(name, bases, dct)

        # Needed for UntypedDeviceBase __init__'s default argument value
        # i.e. device_tag='disk' as specified by specific device class
        if not hasattr(mcs, '_device_tag'):
            raise ValueError(
                "Class %s requires a _device_tag attribute" % name)

        # Same message for both TypedDeviceBase & UntypedDeviceBase subclasses
        message = ("Detected use of a stub device XML for a %s class. These "
                   "only implement a minimal interface that is very likely to "
                   "change in future versions.  This warning will only be "
                   " logged once." % name)

        def issue_warning():
            """
            Closure for created __init__ to only print message once.
            """
            # Examine the CLASS variable
            if not StubDeviceMeta.warning_issued:
                # Set the CLASS variable
                StubDeviceMeta.warning_issued = True
                logging.warning(message)
            else:
                pass  # do nothing

        # Create the proper init function for subclass type
        if TypedDeviceBase in bases:
            # Needed for TypedDeviceBase __init__'s default argument value
            # i.e. type_name='pci' as specified by specific device class.
            if not hasattr(mcs, '_def_type_name'):
                raise ValueError("TypedDevice sub-Class %s must define a "
                                 "_def_type_name attribute" % name)
            # form __init__() and it's arguments for generated class

            def stub_init(self, type_name=getattr(mcs, '_def_type_name'),
                          virsh_instance=base.virsh):
                """
                Initialize stub typed device instance
                """
                # issue warning only when some code instantiats
                # object from generated class
                issue_warning()
                # Created class __init__ still needs to call superclass
                # __init__ (i.e. UntypedDeviceBase or TypedDeviceBase)
                TypedDeviceBase.__init__(self, device_tag=getattr(mcs,
                                                                  '_device_tag'),
                                         type_name=type_name,
                                         virsh_instance=virsh_instance)
        elif UntypedDeviceBase in bases:
            # generate __init__() for untyped devices (similar to above)
            def stub_init(self, virsh_instance=base.virsh):
                """
                Initialize stub un-typed device instance
                """
                issue_warning()
                UntypedDeviceBase.__init__(self, device_tag=getattr(mcs,
                                                                    '_device_tag'),
                                           virsh_instance=virsh_instance)
        else:
            # unexpected usage
            raise TypeError("Class %s is not a subclass of TypedDeviceBase or "
                            "UntypedDeviceBase")
        # Point the generated class's __init__ at the generated function above
        setattr(mcs, '__init__', stub_init)
