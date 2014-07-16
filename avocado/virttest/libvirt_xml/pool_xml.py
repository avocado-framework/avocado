"""
Module simplifying manipulation of XML described at
http://libvirt.org/formatstorage.html#StoragePool
"""
import os
import logging
import tempfile
from autotest.client.shared import error
from virttest import libvirt_storage
from virttest.libvirt_xml import base, xcepts, accessors


class SourceXML(base.LibvirtXMLBase):

    """
    Source block in pool xml, optionally containing different elements and
    attributes which dependent on pool type.
    """

    __slots__ = ('device_path', 'vg_name', 'host_name', 'dir_path',
                 'adp_type', 'adp_name', 'adp_parent', 'adp_wwnn',
                 'adp_wwpn')

    def __init__(self, virsh_instance=base.virsh):
        """
        Create new SourceXML instance.
        """
        accessors.XMLAttribute(property_name='device_path',
                               libvirtxml=self,
                               parent_xpath='/',
                               tag_name='device',
                               attribute='path')
        accessors.XMLElementText(property_name='vg_name',
                                 libvirtxml=self,
                                 parent_xpath='/',
                                 tag_name='name')
        accessors.XMLAttribute(property_name='host_name',
                               libvirtxml=self,
                               parent_xpath='/',
                               tag_name='host',
                               attribute='name')
        accessors.XMLAttribute(property_name='dir_path',
                               libvirtxml=self,
                               parent_xpath='/',
                               tag_name='dir',
                               attribute='path')
        accessors.XMLAttribute(property_name='adp_type',
                               libvirtxml=self,
                               parent_xpath='/',
                               tag_name='adapter',
                               attribute='type')
        accessors.XMLAttribute(property_name='adp_name',
                               libvirtxml=self,
                               parent_xpath='/',
                               tag_name='adapter',
                               attribute='name')
        accessors.XMLAttribute(property_name='adp_parent',
                               libvirtxml=self,
                               parent_xpath='/',
                               tag_name='adapter',
                               attribute='parent')
        accessors.XMLAttribute(property_name='adp_wwnn',
                               libvirtxml=self,
                               parent_xpath='/',
                               tag_name='adapter',
                               attribute='wwnn')
        accessors.XMLAttribute(property_name='adp_wwpn',
                               libvirtxml=self,
                               parent_xpath='/',
                               tag_name='adapter',
                               attribute='wwpn')
        super(SourceXML, self).__init__(virsh_instance=virsh_instance)
        self.xml = u"<source></source>"


class PoolXMLBase(base.LibvirtXMLBase):

    """
    Accessor methods for PoolXML class.

    Properties:
        pool_type:
            string, pool type
        name:
            string, pool name
        uuid:
            string, pool uuid
        capacity:
            integer, pool total capacity
        allocation:
            integer, pool allocated capacity
        available:
            integer, pool available capacity
        source:
            PoolSourceXML instanc
        target:
            string, target path of pool
    """

    __slots__ = ('pool_type', 'name', 'uuid', 'capacity',
                 'allocation', 'available', 'source', 'target_path')
    __uncompareable__ = base.LibvirtXMLBase.__uncompareable__

    __schema_name__ = "pool"

    def __init__(self, virsh_instance=base.virsh):
        accessors.XMLAttribute(property_name='pool_type',
                               libvirtxml=self,
                               parent_xpath='/',
                               tag_name='pool',
                               attribute='type')
        accessors.XMLElementText(property_name='name',
                                 libvirtxml=self,
                                 parent_xpath='/',
                                 tag_name='name')
        accessors.XMLElementText(property_name='uuid',
                                 libvirtxml=self,
                                 parent_xpath='/',
                                 tag_name='uuid')
        accessors.XMLElementInt(property_name='capacity',
                                libvirtxml=self,
                                parent_xpath='/',
                                tag_name='capacity')
        accessors.XMLElementInt(property_name='allocation',
                                libvirtxml=self,
                                parent_xpath='/',
                                tag_name='allocation')
        accessors.XMLElementInt(property_name='available',
                                libvirtxml=self,
                                parent_xpath='/',
                                tag_name='available')
        accessors.XMLElementText(property_name='target_path',
                                 libvirtxml=self,
                                 parent_xpath='/target',
                                 tag_name='path')
        super(PoolXMLBase, self).__init__(virsh_instance=virsh_instance)

    def get_source(self):
        xmltreefile = self.__dict_get__('xml')
        try:
            source_root = xmltreefile.reroot('/source')
        except KeyError, detail:
            raise xcepts.LibvirtXMLError(detail)
        sourcexml = SourceXML(virsh_instance=self.__dict_get__('virsh'))
        sourcexml.xmltreefile = source_root
        return sourcexml

    def del_source(self):
        xmltreefile = self.__dict_get__('xml')
        element = xmltreefile.find('/source')
        if element is not None:
            xmltreefile.remove(element)
            xmltreefile.write()

    def set_source(self, value):
        if not issubclass(type(value), SourceXML):
            raise xcepts.LibvirtXMLError(
                "Value must be a SourceXML or subclass")
        xmltreefile = self.__dict_get__('xml')
        self.del_source()
        root = xmltreefile.getroot()
        root.append(value.xmltreefile.getroot())
        xmltreefile.write()


class PoolXML(PoolXMLBase):

    """
    Manipulators of a libvirt Pool through it's XML definition.
    """

    __slots__ = []

    def __init__(self, pool_type='dir', virsh_instance=base.virsh):
        """
        Initialize new instance with empty XML
        """
        super(PoolXML, self).__init__(virsh_instance=virsh_instance)
        self.xml = u"<pool type='%s'></pool>" % pool_type

    @staticmethod
    def new_from_dumpxml(name, virsh_instance=base.virsh):
        """
        Return new PoolXML instance from virsh pool-dumpxml command

        :param name: Name of pool to pool-dumpxml
        :param virsh_instance: Virsh module or instance to use
        :return: new initialized PoolXML instance
        """
        pool_xml = PoolXML(virsh_instance=virsh_instance)
        pool_xml['xml'] = virsh_instance.pool_dumpxml(name)
        return pool_xml

    @staticmethod
    def get_type(name, virsh_instance=base.virsh):
        """
        Return pool type by pool name

        :param name: pool name
        :return: pool type
        """
        pool_xml = PoolXML.new_from_dumpxml(name, virsh_instance)
        return pool_xml.pool_type

    @staticmethod
    def get_pool_details(name, virsh_instance=base.virsh):
        """
        Return pool details by pool name.

        :param name: pool name
        :return: a dict which include a series of pool details
        """
        pool_xml = PoolXML.new_from_dumpxml(name, virsh_instance)
        pool_details = {}
        pool_details['type'] = pool_xml.pool_type
        pool_details['uuid'] = pool_xml.uuid
        pool_details['capacity'] = pool_xml.capacity
        pool_details['allocation'] = pool_xml.allocation
        pool_details['available'] = pool_xml.available
        pool_details['target_path'] = pool_xml.target_path
        return pool_details

    def pool_undefine(self):
        """
        Undefine pool with libvirt retaining XML in instance
        """
        try:
            self.virsh.pool_undefine(self.name, ignore_status=False)
        except error.CmdError:
            logging.error("Undefine pool '%s' failed.", self.name)
            return False

    def pool_define(self):
        """
        Define pool with virsh from this instance
        """
        result = self.virsh.pool_define(self.xml)
        if result.exit_status:
            logging.error("Define %s failed.\n"
                          "Detail: %s.", self.name, result.stderr)
            return False
        return True

    @staticmethod
    def pool_rename(name, new_name, uuid=None, virsh_instance=base.virsh):
        """
        Rename a pool from pool XML.
        :param name: Original pool name.
        :param new_name: new name of pool.
        :param uuid: new pool uuid, if None libvirt will generate automatically.
        :return:
        """
        pool_ins = libvirt_storage.StoragePool()
        if not pool_ins.is_pool_persistent(name):
            logging.error("Cannot rename for transient pool")
            return False
        start_pool = False
        if pool_ins.is_pool_active(name):
            virsh_instance.pool_destroy(name)
            start_pool = True
        poolxml = PoolXML.new_from_dumpxml(name, virsh_instance)
        backup = poolxml.copy()
        if not pool_ins.delete_pool(name):
            del poolxml
            raise xcepts.LibvirtXMLError("Error occur while deleting pool: %s"
                                         % name)
        # Alter the XML
        poolxml.name = new_name
        if uuid is None:
            del poolxml.uuid
        else:
            poolxml.uuid = uuid
        # Re-define XML to libvirt
        logging.debug("Rename pool: %s to %s.", name, new_name)
        # error message for failed define
        error_msg = "Error reported while defining pool:\n"
        try:
            if not poolxml.pool_define():
                raise xcepts.LibvirtXMLError(error_msg + "%s"
                                             % poolxml.get('xml'))
        except error.CmdError, detail:
            del poolxml
            # Allow exceptions thrown here since state will be undefined
            backup.pool_define()
            raise xcepts.LibvirtXMLError(error_msg + "%s" % detail)
        if start_pool:
            pool_ins.start_pool(new_name)
        return True

    @staticmethod
    def backup_xml(name, virsh_instance=base.virsh):
        """
        Backup the pool xml file.
        """
        try:
            xml_file = tempfile.mktemp(dir="/tmp")
            virsh_instance.pool_dumpxml(name, to_file=xml_file)
            return xml_file
        except Exception, detail:
            if os.path.exists(xml_file):
                os.remove(xml_file)
            logging.error("Failed to backup xml file:\n%s", detail)
            return ""

    def debug_xml(self):
        """
        Dump contents of XML file for debugging
        """
        xml = str(self)
        for debug_line in str(xml).splitlines():
            logging.debug("Pool XML: %s", debug_line)
