"""
Module simplifying manipulation of XML described at
http://libvirt.org/formatnode.html
"""

import os
from virttest.libvirt_xml import base, xcepts, accessors


class CAPXML(base.LibvirtXMLBase):

    """
    The base class for capability.
    """

    def get_sysfs_sub_path(self):
        """
        return the sub path store the info of capibility.
        """
        raise NotImplementedError('get_sysfs_sub_path is not implemented.')

    @staticmethod
    def get_key2filename_dict():
        """
        Return a dict which contain the key and the name
        of info file.
        """
        raise NotImplementedError('get_key2filename_dict is not implemeneted.')

    def get_key2value_dict(self):
        """
        Reutn a dict which contain the key and the value
        in capability xml.
        """
        raise NotImplementedError('get_key2value_dict is not implemented.')


class SystemXML(CAPXML):

    """
    class for capability which type is system.
    """
    __slots__ = ('product', 'hdware_vendor', 'hdware_serial', 'hdware_uuid',
                 'firmware_vendor', 'firmversion', 'firm_release_date')

    __sysfs_sub_path__ = 'dmi/id/'

    __key2filename_dict__ = {'product': 'product_name',
                             'hdware_vendor': 'sys_vendor',
                             'hdware_serial': 'product_serial',
                             'hdware_uuid': 'product_uuid',
                             'firmware_vendor': 'bios_vendor',
                             'firmversion': 'bios_version',
                             'firm_release_date': 'bios_date'}

    @staticmethod
    def get_key2filename_dict():
        """
        Return a dict which contain the key and the name
        of info file for System node device.
        """
        return SystemXML.__key2filename_dict__

    def get_key2value_dict(self):
        """
        return the dict key2value

        key: the key in xml need to check.
        value: value in xml for this key.
        """
        key2value_dict = {}
        for key in SystemXML.__key2filename_dict__:
            key2value_dict[key] = self[key]

        return key2value_dict

    @staticmethod
    def make_sysfs_sub_path():
        """
        return __sysfs_sub_path__ immediately.
        """
        return SystemXML.__sysfs_sub_path__

    def get_sysfs_sub_path(self):
        """
        Return the sysfs_subdir.
        """
        return self.make_sysfs_sub_path()


class NetXML(CAPXML):

    """
    class for capability whose type is net.
    """
    __slots__ = ('interface', 'address')

    def __init__(self, virsh_instance=base.virsh):
        accessors.XMLElementText('interface', self, parent_xpath='/',
                                 tag_name='interface')
        accessors.XMLElementText('address', self, parent_xpath='/',
                                 tag_name='address')


class StorageXML(CAPXML):

    """
    class for capability whose type is storage.
    """
    __slots__ = ('block', 'bus', 'driver_type')

    def __init__(self, virsh_instance=base.virsh):
        accessors.XMLElementText('block', self, parent_xpath='/',
                                 tag_name='block')
        accessors.XMLElementText('bus', self, parent_xpath='/',
                                 tag_name='bus')
        accessors.XMLElementText('driver_type', self, parent_xpath='/',
                                 tag_name='driver_type')


class PCIXML(CAPXML):

    """
    class for capability whose type is pci.
    """
    __slots__ = ('domain', 'bus', 'slot', 'function', 'product_id',
                 'vendor_id')

    def __init__(self, virsh_instance=base.virsh):
        accessors.XMLElementInt('domain', self, parent_xpath='/',
                                tag_name='domain')
        accessors.XMLElementInt('bus', self, parent_xpath='/',
                                tag_name='bus')
        accessors.XMLElementInt('slot', self, parent_xpath='/',
                                tag_name='slot')
        accessors.XMLElementInt('function', self, parent_xpath='/',
                                tag_name='function')
        accessors.XMLAttribute('product_id', self, parent_xpath='/',
                               tag_name='product', attribute='id')
        accessors.XMLAttribute('vendor_id', self, parent_xpath='/',
                               tag_name='vendor', attribute='id')
        super(PCIXML, self).__init__(virsh_instance=virsh_instance)
        self.xml = (' <capability type=\'pci\'></capability>')

    @staticmethod
    def make_sysfs_sub_path(domain, bus, slot, function):
        """
        Make sysfs_sub_path for pci by domain,bus,slot and function.
        """
        pci_bus_path = ("%04x:%02x" % (domain, bus))
        pci_device_path = ("%04x:%02x:%02x.%01x" % (domain, bus,
                                                    slot, function))
        pci_sysfs_sub_path = ("pci_bus/%s/device/%s"
                              % (pci_bus_path, pci_device_path))

        return pci_sysfs_sub_path

    def get_sysfs_sub_path(self):
        """
        Return the sysfs_subdir in .

        Example:
            pci_bus/0000\:00/device/0000\:00\:00.0/
        """
        domain = self.domain
        bus = self.bus
        slot = self.slot
        function = self.function

        return PCIXML.make_sysfs_sub_path(domain, bus, slot, function)

    __key2filename_dict__ = {'product_id': 'device',
                             'vendor_id': 'vendor'}

    @staticmethod
    def get_key2filename_dict():
        """
        return the dict key2filename.
        key: the keys in pcixml need to check.
        filename: the name of file stored info for this key.
        """
        return PCIXML.__key2filename_dict__

    def get_key2value_dict(self):
        """
        return the dict key2value

        key: the key in xml need to check.
        value: value in xml for this key.
        """
        key2value_dict = {}
        for key in PCIXML.__key2filename_dict__:
            key2value_dict[key] = self[key]

        return key2value_dict

    def get_address_dict(self):
        """
        Return a dict contain the address.
        """
        address = {'domain': self.domain, 'bus': self.bus,
                   'slot': self.slot, 'function': self.function}
        return address


class NodedevXMLBase(base.LibvirtXMLBase):

    """
    Accessor methods for NodedevXML class.

    """

    __slots__ = ('name', 'parent', 'cap_type', 'cap',
                 'sysfs_main_path', 'host', 'fc_type',
                 'wwnn', 'wwpn', 'fabric_wwn')

    __schema_name__ = "nodedev"

    __sysfs_dir__ = "/sys/class"

    __type2class_dict__ = {'system': 'SystemXML',
                           'pci': 'PCIXML',
                           'usb_device': 'USBDeviceXML',
                           'usb': 'USBXML',
                           'net': 'NetXML',
                           'scsi_host': 'SCSIHostXML',
                           'scsi': 'SCSIXML',
                           'storage': 'StorageXML'}

    def __init__(self, virsh_instance=base.virsh):
        accessors.XMLElementText('name', self, parent_xpath='/',
                                 tag_name='name')
        accessors.XMLElementText('parent', self, parent_xpath='/',
                                 tag_name='parent')
        accessors.XMLAttribute('cap_type', self, parent_xpath='/',
                               tag_name='capability', attribute='type')
        accessors.XMLElementText('host', self, parent_xpath='/capability',
                                 tag_name='host')
        accessors.XMLAttribute('fc_type', self, parent_xpath='/capability',
                               tag_name='capability', attribute='type')
        accessors.XMLElementText('wwnn', self,
                                 parent_xpath='/capability/capability',
                                 tag_name='wwnn')
        accessors.XMLElementText('wwpn', self,
                                 parent_xpath='/capability/capability',
                                 tag_name='wwpn')
        accessors.XMLElementText('fabric_wwn', self,
                                 parent_xpath='/capability/capability',
                                 tag_name='fabric_wwn')
        super(NodedevXMLBase, self).__init__(virsh_instance=virsh_instance)
        self.xml = '<device></device>'

    @staticmethod
    def get_cap_by_type(cap_type):
        """
        Init a cap class for a specific type.

        :param cap_type: the type of capability.
        :return: instanse of the cap.
        """
        cap_class_name = NodedevXMLBase.__type2class_dict__[cap_type]
        cap_class = globals()[cap_class_name]
        capxml = cap_class()

        return capxml

    def get_cap(self):
        """
        Return the capability of nodedev_xml.
        """
        try:
            cap_root = self.xmltreefile.reroot('/capability')
        except KeyError, detail:
            raise xcepts.LibvirtXMLError(detail)
        capxml = NodedevXMLBase.get_cap_by_type(self.cap_type)
        capxml.xmltreefile = cap_root
        return capxml

    def set_cap(self, value):
        """
        Set the capability by value.
        """
        if not issubclass(type(value), CAPXML):
            raise xcepts.LibvirtXMLError("value must be a CAPXML or subclass")
        # remove any existing capability block
        self.del_cap()
        root = self.xmltreefile.getroot()
        root.append(value.getroot())
        self.xmltreefile.write()

    def del_cap(self):
        """
        Delete the capability from nodedev xml.
        """
        element = self.xmltreefile.find('/capability')
        if element is not None:
            self.mltreefile.remove(element)
        self.xmltreefile.write()

    def get_sysfs_sub_path(self):
        """
        Get the sub sysfs path of the capability.
        """
        capxml = self.cap
        sysfs_sub_path = capxml.get_sysfs_sub_path()

        return sysfs_sub_path

    def get_sysfs_path(self):
        """
        Get the abs path of the capability info.
        """
        sysfs_main_path = self.__sysfs_dir__
        sysfs_sub_path = self.get_sysfs_sub_path()

        sysfs_path = os.path.join(sysfs_main_path, sysfs_sub_path)
        return sysfs_path


class NodedevXML(NodedevXMLBase):

    """
    class for Node device XML.
    """

    __slots__ = []

    def __init__(self, virsh_instance=base.virsh):
        """
        Initialize new instance.
        """
        super(NodedevXML, self).__init__(virsh_instance=virsh_instance)
        self.xml = ('<device></device>')

    @staticmethod
    def new_from_dumpxml(dev_name, virsh_instance=base.virsh):
        """
        Get a instance of NodedevXML by dumpxml dev_name.
        """
        nodedevxml = NodedevXML(virsh_instance=virsh_instance)
        dumpxml_result = virsh_instance.nodedev_dumpxml(dev_name)
        if dumpxml_result.exit_status:
            raise xcepts.LibvirtXMLError("Nodedev_dumpxml %s failed.\n"
                                         "Error: %s."
                                         % (dev_name, dumpxml_result.stderr))
        nodedevxml.xml = dumpxml_result.stdout

        return nodedevxml

    def get_key2value_dict(self):
        """
        Get the dict which contain key and value in xml.
        key: keys in nodedev xml need to check.
        value: value in xml for the key.
        """
        capxml = self.cap
        key2value_dict = capxml.get_key2value_dict()

        return key2value_dict

    def get_key2syspath_dict(self):
        """
        Get the dict which contains key and path.
        key: keys in nodedev xml need to check.
        syspath: the abs path for the file stores info for the key.
        """
        sysfs_path = self.get_sysfs_path()
        capxml = self.cap
        key2filename_dict = capxml.__class__.get_key2filename_dict()

        key2syspath_dict = {}
        for key in key2filename_dict:
            filename = key2filename_dict[key]
            abs_syspath = os.path.join(sysfs_path, filename)
            key2syspath_dict[key] = abs_syspath

        return key2syspath_dict
