"""
Module simplifying manipulation of XML described at
http://libvirt.org/formatstorage.html#StorageVol
"""

from virttest.libvirt_xml import base, accessors


class VolXMLBase(base.LibvirtXMLBase):

    """
    Accessor methods for VolXML class.

    Properties:
        name: string, operates on XML name tag
        key: string, operates on key tag
        capacity: integer, operates on capacity attribute of capacity tag
        allocation: integer, operates on allocation attribute of allocation
        format: string, operates on type attribute of format tag
        path: string, operates on path attribute of path tag
        owner, integer, operates on owner attribute of owner tag
        group, integer, operates on group attribute of group tag
        mode: string, operates on mode attribute of mode tag
        label: string, operates on label attribute of label tag
        compat: string, operates on compat attribute of label tag
        lazy_refcounts: bool, True/False
        encryption: VolXMLBase.Encryption instance.
        capacity_unit: string, operates on unit attribute of capacity tag
    """

    __slots__ = ('name', 'key', 'capacity', 'allocation', 'format', 'path',
                 'owner', 'group', 'mode', 'label', 'compat', 'lazy_refcounts',
                 'encryption', "capacity_unit")

    __uncompareable__ = base.LibvirtXMLBase.__uncompareable__

    __schema_name__ = "storagevol"

    def __init__(self, virsh_instance=base.virsh):
        accessors.XMLElementText('name', self, parent_xpath='/',
                                 tag_name='name')
        accessors.XMLElementText('key', self, parent_xpath='/',
                                 tag_name='key')
        accessors.XMLElementInt('capacity', self, parent_xpath='/',
                                tag_name='capacity')
        accessors.XMLElementInt('allocation', self, parent_xpath='/',
                                tag_name='allocation')
        accessors.XMLAttribute('format', self, parent_xpath='/target',
                               tag_name='format', attribute='type')
        accessors.XMLAttribute('capacity_unit', self, parent_xpath='/',
                               tag_name='capacity', attribute='unit')
        accessors.XMLElementNest('encryption', self, parent_xpath='/target',
                                 tag_name='encryption', subclass=self.Encryption,
                                 subclass_dargs={
                                     'virsh_instance': virsh_instance})
        accessors.XMLElementText('path', self, parent_xpath='/target',
                                 tag_name='path')
        accessors.XMLElementInt('owner', self,
                                parent_xpath='/target/permissions',
                                tag_name='owner')
        accessors.XMLElementInt('group', self,
                                parent_xpath='/target/permissions',
                                tag_name='group')
        accessors.XMLElementText('mode', self,
                                 parent_xpath='/target/permissions',
                                 tag_name='mode')
        accessors.XMLElementText('label', self,
                                 parent_xpath='/target/permissions',
                                 tag_name='label')
        accessors.XMLElementText('compat', self, parent_xpath='/target',
                                 tag_name='compat')
        accessors.XMLElementBool('lazy_refcounts', self,
                                 parent_xpath='/target/features',
                                 tag_name='lazy_refcounts')
        super(VolXMLBase, self).__init__(virsh_instance=virsh_instance)


class VolXML(VolXMLBase):

    """
    Manipulators of a Virtual Vol through it's XML definition.
    """

    __slots__ = []

    def __init__(self, vol_name='default', virsh_instance=base.virsh):
        """
        Initialize new instance with empty XML
        """
        super(VolXML, self).__init__(virsh_instance=virsh_instance)
        self.xml = u"<volume><name>%s</name></volume>" % vol_name

    def new_encryption(self, **dargs):
        """
        Return a new volume encryption instance and set properties from dargs
        """
        new_one = self.Encryption(virsh_instance=self.virsh)
        for key, value in dargs.items():
            setattr(new_one, key, value)
        return new_one

    def create(self, pool_name, virsh_instance=base.virsh):
        """
        Create volume with virsh from this instance
        """
        result = virsh_instance.vol_create(pool_name, self.xml)
        if result.exit_status:
            return False
        return True

    @staticmethod
    def new_from_vol_dumpxml(vol_name, pool_name, virsh_instance=base.virsh):
        """
        Return new VolXML instance from virsh vol-dumpxml command

        :param vol_name: Name of vol to vol-dumpxml
        :param virsh_instance: virsh module or instance to use
        :return: New initialized VolXML instance
        """
        volxml = VolXML(virsh_instance=virsh_instance)
        volxml['xml'] = virsh_instance.vol_dumpxml(vol_name, pool_name)\
                                      .stdout.strip()
        return volxml

    @staticmethod
    def get_vol_details_by_name(vol_name, pool_name, virsh_instance=base.virsh):
        """
        Return volume xml dictionary by Vol's uuid or name.

        :param vol_name: Vol's name
        :return: volume xml dictionary
        """
        volume_xml = {}
        vol_xml = VolXML.new_from_vol_dumpxml(vol_name, pool_name,
                                              virsh_instance)
        volume_xml['key'] = vol_xml.key
        volume_xml['path'] = vol_xml.path
        volume_xml['format'] = vol_xml.format
        volume_xml['capacity'] = vol_xml.capacity
        volume_xml['allocation'] = vol_xml.allocation
        return volume_xml

    @staticmethod
    def new_vol(**dargs):
        """
        Return a new VolXML instance and set properties from dargs

        :param dargs: param dictionary
        :return: new VolXML instance
        """
        new_one = VolXML(virsh_instance=base.virsh)
        for key, value in dargs.items():
            setattr(new_one, key, value)
        return new_one

    class Encryption(base.LibvirtXMLBase):

        """
        Encryption volume XML class

        Properties:

        format:
            string.
        secret:
            dict, keys: type, uuid
        """

        __slots__ = ('format', 'secret')

        def __init__(self, virsh_instance=base.virsh):
            accessors.XMLAttribute('format', self, parent_xpath='/',
                                   tag_name='encryption', attribute='format')
            accessors.XMLElementDict('secret', self, parent_xpath='/',
                                     tag_name='secret')
            super(VolXML.Encryption, self).__init__(virsh_instance=virsh_instance)
            self.xml = '<encryption/>'
