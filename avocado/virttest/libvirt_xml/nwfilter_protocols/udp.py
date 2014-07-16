"""
udp protocl support class(es)

http://libvirt.org/formatnwfilter.html#nwfelemsRulesProtoTCP-ipv4
"""

from virttest.libvirt_xml import accessors, xcepts
from virttest.libvirt_xml.nwfilter_protocols import base


class Udp(base.TypedDeviceBase):

    """
    Create new Udp xml instances

    Properties:
        attrs: libvirt_xml.nwfilter_protocols.Udp.Attr instance
    """

    __slots__ = ('attrs',)

    def __init__(self, type_name='file', virsh_instance=base.base.virsh):
        accessors.XMLElementNest('attrs', self, parent_xpath='/',
                                 tag_name='udp', subclass=self.Attr,
                                 subclass_dargs={
                                     'virsh_instance': virsh_instance})
        super(Udp, self).__init__(protocol_tag='udp', type_name=type_name,
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
        Return udp attribute dict

        :return: None if no udp in xml, dict of udp's attributes.
        """
        try:
            udp_node = self.xmltreefile.reroot('/udp')
        except KeyError, detail:
            raise xcepts.LibvirtXMLError(detail)
        node = udp_node.getroot()
        udp_attr = dict(node.items())

        return udp_attr

    class Attr(base.base.LibvirtXMLBase):

        """
        Udp attribute XML class

        Properties:

        srcmacaddr: string, MAC address of sender
        srcipaddr: string, Source IP address
        srcipmask: string, Mask applied to source IP address
        dstipaddr: string, Destination IP address
        dstipmask: string, Mask applied to destination IP address
        srcipfrom: string, Start of range of source IP address
        srcipto: string, End of range of source IP address
        dstipfrom: string, Start of range of destination IP address
        dstipto: string, End of range of destination IP address
        srcportstart: string, Start of range of valid source ports; requires protocol
        srcportend: string, End of range of valid source ports; requires protocol
        dstportstart: string, Start of range of valid destination ports; requires protocol
        dstportend: string, End of range of valid destination ports; requires protocol
        comment: string, text with max. 256 characters
        state: string, comma separated list of NEW,ESTABLISHED,RELATED, INVALID or NONE
        ipset: The name of an IPSet managed outside of libvirt
        ipsetflags: flags for the IPSet; requires ipset attribute
        """

        __slots__ = ('srcmacaddr', 'srcipaddr', 'srcipmask', 'dstipaddr',
                     'dstipmask', 'srcipfrom', 'srcipto', 'dstipfrom',
                     'dstipto', 'srcportstart', 'srcportend', 'dstportstart',
                     'dstportend', 'dscp', 'comment', 'state', 'ipset',
                     'ipsetflags')

        def __init__(self, virsh_instance=base.base.virsh):
            accessors.XMLAttribute('srcmacaddr', self, parent_xpath='/',
                                   tag_name='udp', attribute='srcmacaddr')
            accessors.XMLAttribute('srcipaddr', self, parent_xpath='/',
                                   tag_name='udp', attribute='srcipaddr')
            accessors.XMLAttribute('srcipmask', self, parent_xpath='/',
                                   tag_name='udp', attribute='srcipmask')
            accessors.XMLAttribute('dstipaddr', self, parent_xpath='/',
                                   tag_name='udp', attribute='dstipaddr')
            accessors.XMLAttribute('dstipmask', self, parent_xpath='/',
                                   tag_name='udp', attribute='dstipmask')
            accessors.XMLAttribute('srcipfrom', self, parent_xpath='/',
                                   tag_name='udp', attribute='srcipfrom')
            accessors.XMLAttribute('srcipto', self, parent_xpath='/',
                                   tag_name='udp', attribute='srcipto')
            accessors.XMLAttribute('dstipfrom', self, parent_xpath='/',
                                   tag_name='udp', attribute='dstipfrom')
            accessors.XMLAttribute('dstipto', self, parent_xpath='/',
                                   tag_name='udp', attribute='dstipto')
            accessors.XMLAttribute('srcportstart', self, parent_xpath='/',
                                   tag_name='udp', attribute='srcportstart')
            accessors.XMLAttribute('srcportend', self, parent_xpath='/',
                                   tag_name='udp', attribute='srcportend')
            accessors.XMLAttribute('dstportstart', self, parent_xpath='/',
                                   tag_name='udp', attribute='dstportstart')
            accessors.XMLAttribute('dstportend', self, parent_xpath='/',
                                   tag_name='udp', attribute='dstportend')
            accessors.XMLAttribute('dscp', self, parent_xpath='/',
                                   tag_name='udp', attribute='dscp')
            accessors.XMLAttribute('comment', self, parent_xpath='/',
                                   tag_name='udp', attribute='comment')
            accessors.XMLAttribute('state', self, parent_xpath='/',
                                   tag_name='udp', attribute='state')
            accessors.XMLAttribute('ipset', self, parent_xpath='/',
                                   tag_name='udp', attribute='ipset')
            accessors.XMLAttribute('ipsetflags', self, parent_xpath='/',
                                   tag_name='udp', attribute='ipsetflags')

            super(self.__class__, self).__init__(virsh_instance=virsh_instance)
            self.xml = '<udp/>'
