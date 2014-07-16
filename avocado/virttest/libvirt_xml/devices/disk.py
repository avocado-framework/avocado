"""
disk device support class(es)

http://libvirt.org/formatdomain.html#elementsDisks
"""

from virttest.libvirt_xml import accessors, xcepts
from virttest.libvirt_xml.devices import base, librarian


class Disk(base.TypedDeviceBase):

    """
    Disk device XML class

    Properties:
        device:
            string, how exposted to guest
        rawio:
            string (yes/no), disk needs rawio capability
        sgio:
            string, "filtered" or "unfiltered"
        snapshot:
            string, "yes", "no", "internal" or "external"
        wwn:
            string.
        serial:
            string.
        vendor:
            string.
        product:
            string.
        driver:
            dict, keys: name, type, cache, error_policy, io, ioeventfd,
            event_idx, copy_on_read, discard
        target:
            dict, keys: dev, bus, tray
        blockio:
            dict, keys: logical_block_size, physical_block_size
        geometry:
            dict, keys: cyls, heads, secs, trans
        address:
            libvirt_xml.devices.Address instance
        boot:
            string, boot order number to use if not using boot in os element
        readonly:
            bool, True/False
        transient:
            bool, True/False
        share:
            bool, True/False
        mirror:
            bool, read-only, True if block copy started
        ready:
            bool, read-only, True if disk ready for pivot
        iotune:
            libvirt_xml.devices.Disk.IOTune instance
        source:
            libvirt_xml.devices.Disk.DiskSource instance
        encryption:
            libvirt_xml.devices.Disk.Encryption instance.
    """

    __slots__ = ('device', 'rawio', 'sgio', 'snapshot', 'driver', 'target',
                 'address', 'boot', 'readonly', 'transient', 'share',
                 'mirror', 'ready', 'iotune', 'source', 'blockio', 'geometry',
                 'wwn', 'serial', 'vendor', 'product', 'encryption')

    def __init__(self, type_name='file', virsh_instance=base.base.virsh):
        accessors.XMLAttribute('device', self, parent_xpath='/',
                               tag_name='disk', attribute='device')
        accessors.XMLAttribute('rawio', self, parent_xpath='/',
                               tag_name='disk', attribute='rawio')
        accessors.XMLAttribute('sgio', self, parent_xpath='/',
                               tag_name='disk', attribute='sgio')
        accessors.XMLAttribute('snapshot', self, parent_xpath='/',
                               tag_name='disk', attribute='snapshot')
        accessors.XMLElementText('wwn', self, parent_xpath='/',
                                 tag_name='wwn')
        accessors.XMLElementText('serial', self, parent_xpath='/',
                                 tag_name='serial')
        accessors.XMLElementText('vendor', self, parent_xpath='/',
                                 tag_name='vendor')
        accessors.XMLElementText('product', self, parent_xpath='/',
                                 tag_name='product')
        accessors.XMLElementDict('driver', self, parent_xpath='/',
                                 tag_name='driver')
        accessors.XMLElementDict('target', self, parent_xpath='/',
                                 tag_name='target')
        accessors.XMLElementDict('blockio', self, parent_xpath='/',
                                 tag_name='blockio')
        accessors.XMLElementDict('geometry', self, parent_xpath='/',
                                 tag_name='geometry')
        accessors.XMLElementNest('address', self, parent_xpath='/',
                                 tag_name='address', subclass=self.Address,
                                 subclass_dargs={'type_name': 'drive',
                                                 'virsh_instance': virsh_instance})
        accessors.XMLAttribute('boot', self, parent_xpath='/',
                               tag_name='boot', attribute='order')
        accessors.XMLElementBool('readonly', self, parent_xpath='/',
                                 tag_name='readonly')
        accessors.XMLElementBool('transient', self, parent_xpath='/',
                                 tag_name='transient')
        accessors.XMLElementBool('share', self, parent_xpath='/',
                                 tag_name='shareable')
        accessors.XMLElementNest('source', self, parent_xpath='/',
                                 tag_name='source', subclass=self.DiskSource,
                                 subclass_dargs={
                                     'virsh_instance': virsh_instance})
        ro = ['set', 'del']
        accessors.XMLElementBool('mirror', self, forbidden=ro,
                                 parent_xpath='/', tag_name='mirror')
        accessors.XMLElementBool('ready', self, forbidden=ro,
                                 parent_xpath='/', tag_name='ready')
        accessors.XMLElementNest('iotune', self, parent_xpath='/',
                                 tag_name='iotune', subclass=self.IOTune,
                                 subclass_dargs={
                                     'virsh_instance': virsh_instance})
        accessors.XMLElementNest('encryption', self, parent_xpath='/',
                                 tag_name='encryption', subclass=self.Encryption,
                                 subclass_dargs={
                                     'virsh_instance': virsh_instance})
        super(Disk, self).__init__(device_tag='disk', type_name=type_name,
                                   virsh_instance=virsh_instance)

    def new_disk_source(self, **dargs):
        """
        Return a new disk source instance and set properties from dargs
        """
        new_one = self.DiskSource(virsh_instance=self.virsh)
        for key, value in dargs.items():
            setattr(new_one, key, value)
        return new_one

    def new_iotune(self, **dargs):
        """
        Return a new disk IOTune instance and set properties from dargs
        """
        new_one = self.IOTune(virsh_instance=self.virsh)
        for key, value in dargs.items():
            setattr(new_one, key, value)
        return new_one

    def new_encryption(self, **dargs):
        """
        Return a new disk encryption instance and set properties from dargs
        """
        new_one = self.Encryption(virsh_instance=self.virsh)
        for key, value in dargs.items():
            setattr(new_one, key, value)
        return new_one

    def new_disk_address(self, type_name='drive', **dargs):
        """
        Return a new disk Address instance and set properties from dargs
        """
        new_one = self.Address(type_name=type_name, virsh_instance=self.virsh)
        for key, value in dargs.items():
            setattr(new_one, key, value)
        return new_one

    # For convenience
    Address = librarian.get('address')

    class DiskSource(base.base.LibvirtXMLBase):

        """
        Disk source device XML class

        Properties:

        attrs: Dictionary of attributes, qualifying the disk type
        seclabels: list of libvirt_xml.devices.seclabel.Seclabel instances
        hosts: list of dictionaries describing network host properties
        """

        __slots__ = ('attrs', 'seclabels', 'hosts',)

        def __init__(self, virsh_instance=base.base.virsh):
            accessors.XMLElementDict('attrs', self, parent_xpath='/',
                                     tag_name='source')
            accessors.XMLElementList('seclabels', self, parent_xpath='/',
                                     marshal_from=self.marshal_from_seclabel,
                                     marshal_to=self.marshal_to_seclabel)
            accessors.XMLElementList('hosts', self, parent_xpath='/',
                                     marshal_from=self.marshal_from_host,
                                     marshal_to=self.marshal_to_host)
            super(self.__class__, self).__init__(virsh_instance=virsh_instance)
            self.xml = '<source/>'

        @staticmethod
        def marshal_from_seclabel(item, index, libvirtxml):
            """Convert a Seclabel instance into tag + attributes"""
            del index           # not used
            del libvirtxml      # not used
            root = item.xmltreefile.getroot()
            if root.tag == 'seclabel':
                return (root.tag, dict(root.items))
            else:
                raise xcepts.LibvirtXMLError("Expected a list of seclabel "
                                             "instances, not a %s" % str(item))

        @staticmethod
        def marshal_to_seclabel(tag, attr_dict, index, libvirtxml):
            """Convert a tag + attributes into a Seclabel instance"""
            del index           # not used
            if tag != 'seclabel':
                return None     # Don't convert this item
            Seclabel = librarian.get('seclabel')
            newone = Seclabel(virsh_instance=libvirtxml.virsh)
            newone.update(attr_dict)
            return newone

        @staticmethod
        def marshal_from_host(item, index, libvirtxml):
            """Convert a dictionary into a tag + attributes"""
            del index           # not used
            del libvirtxml      # not used
            if not isinstance(item, dict):
                raise xcepts.LibvirtXMLError("Expected a dictionary of host "
                                             "attributes, not a %s"
                                             % str(item))
            return ('host', dict(item))  # return copy of dict, not reference

        @staticmethod
        def marshal_to_host(tag, attr_dict, index, libvirtxml):
            """Convert a tag + attributes into a dictionary"""
            del index                    # not used
            del libvirtxml               # not used
            if tag != 'host':
                return None              # skip this one
            return dict(attr_dict)       # return copy of dict, not reference

    class IOTune(base.base.LibvirtXMLBase):

        """
        IOTune device XML class

        Properties:

        total_bytes_sec: str(int)
        read_bytes_sec: str(int)
        write_bytes_sec: str(int)
        total_iops_sec: str(int)
        read_iops_sec: str(int)
        write_iops_sec: str(int)
        """

        __slots__ = ('total_bytes_sec', 'read_bytes_sec', 'write_bytes_sec',
                     'total_iops_sec', 'read_iops_sec', 'write_iops_sec')

        def __init__(self, virsh_instance=base.base.virsh):
            for slot in self.__all_slots__:
                if slot in base.base.LibvirtXMLBase.__all_slots__:
                    continue    # don't add these
                else:
                    accessors.XMLElementInt(slot, self, parent_xpath='/',
                                            tag_name=slot)
            super(Disk.IOTune, self).__init__(virsh_instance=virsh_instance)
            self.xml = '<iotune/>'

    class Encryption(base.base.LibvirtXMLBase):

        """
        Encryption device XML class

        Properties:

        encryption:
            string.
        secret:
            dict, keys: type, uuid
        """

        __slots__ = ('encryption', 'secret')

        def __init__(self, virsh_instance=base.base.virsh):
            accessors.XMLAttribute('encryption', self, parent_xpath='/',
                                   tag_name='encryption', attribute='format')
            accessors.XMLElementDict('secret', self, parent_xpath='/',
                                     tag_name='secret')
            super(Disk.Encryption, self).__init__(virsh_instance=virsh_instance)
            self.xml = '<encryption/>'
