"""
arp protocl support class(es)

http://libvirt.org/formatnwfilter.html#nwfelemsRulesProtoARP
"""

from virttest.libvirt_xml import accessors, xcepts
from virttest.libvirt_xml.nwfilter_protocols import base


class Arp(base.TypedDeviceBase):

    """
    Create new Arp xml instances

    Properties:

    attrs: libvirt_xml.nwfilter_protocols.Arp.Attr instance
    """

    __slots__ = ('attrs',)

    def __init__(self, type_name='file', virsh_instance=base.base.virsh):
        accessors.XMLElementNest('attrs', self, parent_xpath='/',
                                 tag_name='arp', subclass=self.Attr,
                                 subclass_dargs={
                                     'virsh_instance': virsh_instance})
        super(Arp, self).__init__(protocol_tag='arp', type_name=type_name,
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
        Return arp attribute dict

        :return: None if no arp in xml, dict of arp's attributes.
        """
        try:
            arp_node = self.xmltreefile.reroot('/arp')
        except KeyError, detail:
            raise xcepts.LibvirtXMLError(detail)
        node = arp_node.getroot()
        arp_attr = dict(node.items())

        return arp_attr

    class Attr(base.base.LibvirtXMLBase):

        """
        Arp attribute XML class

        Properties:

        srcmacaddr: string, MAC address of sender
        srcmacmask: string, Mask applied to MAC address of sender
        dstmacaddr: string, MAC address of destination
        dstmacaddr: string, Mask applied to MAC address of destination
        hwtype: string, Hardware type
        protocoltype: string, Protocol type
        opcode: string, Opcode
        arpsrcmacaddr: string, Source MAC address in ARP/RARP packet
        arpdstmacaddr: string, Destination MAC address in ARP/RARP packet
        arpsrcipaddr: string, Source IP address in ARP/RARP packet
        arpdstipaddr: string, Destination IP address in ARP/RARP packet
        comment: string, text with max. 256 characters
        gratuitous: string, boolean indicating whether to check for gratuitous ARP packet
        """

        __slots__ = ('srcmacaddr', 'srcmacmask', 'dstmacaddr', 'dstmacmask',
                     'hwtype', 'protocoltype', 'opcode', 'arpsrcmacaddr',
                     'arpdstmacaddr', 'arpsrcipaddr', 'arpdstipaddr',
                     'comment', 'gratuitous')

        def __init__(self, virsh_instance=base.base.virsh):
            accessors.XMLAttribute('srcmacaddr', self, parent_xpath='/',
                                   tag_name='arp', attribute='srcmacaddr')
            accessors.XMLAttribute('srcmacmask', self, parent_xpath='/',
                                   tag_name='arp', attribute='srcmacmask')
            accessors.XMLAttribute('dstmacaddr', self, parent_xpath='/',
                                   tag_name='arp', attribute='dstmacaddr')
            accessors.XMLAttribute('dstmacmask', self, parent_xpath='/',
                                   tag_name='arp', attribute='dstmacmask')
            accessors.XMLAttribute('hwtype', self, parent_xpath='/',
                                   tag_name='arp', attribute='hwtype')
            accessors.XMLAttribute('protocoltype', self, parent_xpath='/',
                                   tag_name='arp', attribute='protocoltype')
            accessors.XMLAttribute('opcode', self, parent_xpath='/',
                                   tag_name='arp', attribute='opcode')
            accessors.XMLAttribute('arpsrcmacaddr', self, parent_xpath='/',
                                   tag_name='arp', attribute='arpsrcmacaddr')
            accessors.XMLAttribute('arpdstmacaddr', self, parent_xpath='/',
                                   tag_name='arp', attribute='arpdstmacaddr')
            accessors.XMLAttribute('arpsrcipaddr', self, parent_xpath='/',
                                   tag_name='arp', attribute='arpsrcipaddr')
            accessors.XMLAttribute('arpdstipaddr', self, parent_xpath='/',
                                   tag_name='arp', attribute='arpdstipaddr')
            accessors.XMLAttribute('comment', self, parent_xpath='/',
                                   tag_name='arp', attribute='comment')
            accessors.XMLAttribute('gratuitous', self, parent_xpath='/',
                                   tag_name='arp', attribute='gratuitous')

            super(self.__class__, self).__init__(virsh_instance=virsh_instance)
            self.xml = '<arp/>'
