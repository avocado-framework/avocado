"""
Module simplifying manipulation of XML described at
http://libvirt.org/formatsecret.html
"""

from virttest.libvirt_xml import base, accessors


class SecretXMLBase(base.LibvirtXMLBase):

    """
    Accessor methods for SecretXML class.

    Properties:
        secret_ephemeral:
            yes or no, operates on XML secret tag
        secret_private:
            yes or no, operates on XML secret tag
        description:
            string, operates on description tag
        uuid:
            string, operates on uuid tag
        usage:
            string, operates on usage tag
        volume:
            the volume file path, sub-tag of the usage tag,
            operates on volume tag
    """

    __slots__ = ('secret_ephemeral', 'secret_private', 'description',
                 'uuid', 'usage', 'volume')

    __uncompareable__ = base.LibvirtXMLBase.__uncompareable__

    __schema_name__ = "secret"

    def __init__(self, virsh_instance=base.virsh):
        accessors.XMLAttribute('secret_ephemeral', self, parent_xpath='/',
                               tag_name='secret', attribute='ephemeral')
        accessors.XMLAttribute('secret_private', self, parent_xpath='/',
                               tag_name='secret', attribute='private')
        accessors.XMLElementText('uuid', self, parent_xpath='/',
                                 tag_name='uuid')
        accessors.XMLElementText('description', self, parent_xpath='/',
                                 tag_name='description')
        accessors.XMLAttribute('usage', self, parent_xpath='/',
                               tag_name='usage', attribute='type')
        accessors.XMLElementText('volume', self, parent_xpath='/usage',
                                 tag_name='volume')
        super(SecretXMLBase, self).__init__(virsh_instance=virsh_instance)


class SecretXML(SecretXMLBase):

    """
    Manipulators of a secret through it's XML definition.
    """

    __slots__ = []

    def __init__(self, ephemeral='yes', private='no',
                 virsh_instance=base.virsh):
        """
        Initialize new instance with empty XML
        """
        super(SecretXML, self).__init__(virsh_instance=virsh_instance)
        self.xml = u"<secret ephemeral='%s' private='%s'><description>\
                     </description></secret>" % (ephemeral, private)

    @staticmethod
    def new_from_secret_dumpxml(uuid, virsh_instance=base.virsh):
        """
        Return new SecretXML instance from virsh secret-dumpxml command

        :param uuid: secret's uuid
        :param virsh_instance: virsh module or instance to use
        :return: New initialized SecretXML instance
        """
        secret_xml = SecretXML(virsh_instance=virsh_instance)
        secret_xml['xml'] = virsh_instance.secret_dumpxml(uuid).stdout.strip()

        return secret_xml

    @staticmethod
    def get_secret_details_by_uuid(uuid, virsh_instance=base.virsh):
        """
        Return secret XML by secret's uuid

        :param uuid: secret's uuid
        :return: secret XML dictionary
        """
        secret_xml = {}
        sec_xml = SecretXML.new_from_secret_dumpxml(uuid, virsh_instance)

        secret_xml['secret_ephemeral'] = sec_xml.secret_ephemeral
        secret_xml['secret_private'] = sec_xml.secret_private
        secret_xml['uuid'] = sec_xml.uuid
        secret_xml['description'] = sec_xml.description
        secret_xml['usage'] = sec_xml.usage
        secret_xml['volume'] = sec_xml.volume

        return secret_xml
