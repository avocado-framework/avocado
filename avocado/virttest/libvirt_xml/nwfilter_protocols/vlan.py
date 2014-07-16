"""
vlan protocl support class(es)

http://libvirt.org/formatnwfilter.html#nwfelemsRulesProtoVLAN
"""

from virttest.libvirt_xml import accessors, xcepts
from virttest.libvirt_xml.nwfilter_protocols import base


class Vlan(base.TypedDeviceBase):

    """
    Create new Vlan xml instances

    Properties:
        attrs: libvirt_xml.nwfilter_protocols.Vlan.Attr instance
    """

    __slots__ = ('attrs',)

    def __init__(self, type_name='file', virsh_instance=base.base.virsh):
        accessors.XMLElementNest('attrs', self, parent_xpath='/',
                                 tag_name='vlan', subclass=self.Attr,
                                 subclass_dargs={
                                     'virsh_instance': virsh_instance})
        super(Vlan, self).__init__(protocol_tag='vlan', type_name=type_name,
                                   virsh_instance=virsh_instance)

    def new_attr(self, **dargs):
        """
        Return a new Attr instance and set properties from dargs

        :param dargs: dict of attributes
        :return: new Attr instance
        """
        new_one = self.Attr(virsh_instance=self.virsh)
        for key, value in dargs.items():
            setattr(new_one, key, value)
        return new_one

    def get_attr(self):
        """
        Return vlan attribute dict

        :return: None if no vlan in xml, dict of vlan's attributes.
        """
        try:
            vlan_node = self.xmltreefile.reroot('/vlan')
        except KeyError, detail:
            raise xcepts.LibvirtXMLError(detail)
        node = vlan_node.getroot()
        vlan_attr = dict(node.items())

        return vlan_attr

    class Attr(base.base.LibvirtXMLBase):

        """
        Vlan attribute XML class

        Properties:

        srcmacaddr: string, MAC address of sender
        srcmacmask: string, Mask applied to MAC address of sender
        dstmacaddr: string, MAC address of destination
        dstmacaddr: string, Mask applied to MAC address of destination
        vlanid: string, VLAN ID
        encap_protocol: string, Encapsulated layer 3 protocol ID
        comment: string, text with max. 256 characters
        """

        __slots__ = ('srcmacaddr', 'srcmacmask', 'dstmacaddr', 'dstmacmask',
                     'vlanid', 'encap_protocol', 'comment')

        def __init__(self, virsh_instance=base.base.virsh):
            accessors.XMLAttribute('srcmacaddr', self, parent_xpath='/',
                                   tag_name='vlan', attribute='srcmacaddr')
            accessors.XMLAttribute('srcmacmask', self, parent_xpath='/',
                                   tag_name='vlan', attribute='srcmacmask')
            accessors.XMLAttribute('dstmacaddr', self, parent_xpath='/',
                                   tag_name='vlan', attribute='dstmacaddr')
            accessors.XMLAttribute('dstmacmask', self, parent_xpath='/',
                                   tag_name='vlan', attribute='dstmacmask')
            accessors.XMLAttribute('vlanid', self, parent_xpath='/',
                                   tag_name='vlan', attribute='vlanid')
            accessors.XMLAttribute('encap_protocol', self, parent_xpath='/',
                                   tag_name='vlan', attribute='encap-protocol')
            accessors.XMLAttribute('comment', self, parent_xpath='/',
                                   tag_name='vlan', attribute='comment')

            super(self.__class__, self).__init__(virsh_instance=virsh_instance)
            self.xml = '<vlan/>'
