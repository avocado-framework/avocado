"""
all-ipv6 protocl support class(es)

http://libvirt.org/formatnwfilter.html#nwfelemsRulesProtoMiscv6
"""

from virttest.libvirt_xml import accessors, xcepts
from virttest.libvirt_xml.nwfilter_protocols import base


class All_ipv6(base.TypedDeviceBase):

    """
    Create new All_ipv6 xml instances

    Properties:
        attrs: libvirt_xml.nwfilter_protocols.All_ipv6.Attr instance
    """

    __slots__ = ('attrs',)

    def __init__(self, type_name='file', virsh_instance=base.base.virsh):
        accessors.XMLElementNest('attrs', self, parent_xpath='/',
                                 tag_name='all_ipv6', subclass=self.Attr,
                                 subclass_dargs={
                                     'virsh_instance': virsh_instance})
        super(All_ipv6, self).__init__(protocol_tag='all-ipv6',
                                       type_name=type_name,
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
        Return all-ipv6 attribute dict

        :return: None if no all-ipv6 in xml, dict of all-ipv6's attributes.
        """
        try:
            all_node = self.xmltreefile.reroot('/all-ipv6')
        except KeyError, detail:
            raise xcepts.LibvirtXMLError(detail)
        node = all_node.getroot()
        all_attr = dict(node.items())

        return all_attr

    class Attr(base.base.LibvirtXMLBase):

        """
        All_ipv6 attribute XML class


        Properties:

        srcmacaddr: string, MAC address of sender
        srcmacmask: string, Mask applied to MAC address of sender
        dstmacaddr: string, MAC address of destination
        dstmacmask: string, Mask applied to MAC address of destination
        srcipaddr: string, Source IP address
        srcipmask: string, Mask applied to source IP address
        dstipaddr: string, Destination IP address
        dstipmask: string, Mask applied to destination IP address
        srcipfrom: string, Start of range of source IP address
        srcipto: string, End of range of source IP address
        dstipfrom: string, Start of range of destination IP address
        dstipto: string, End of range of destination IP address
        comment: string, text with max. 256 characters
        state: string, comma separated list of NEW,ESTABLISHED,RELATED,INVALID or NONE
        ipset: The name of an IPSet managed outside of libvirt
        ipsetflags: flags for the IPSet; requires ipset attribute
        """

        __slots__ = ('srcmacaddr', 'srcmacmask', 'dstmacaddr', 'dstmacmask',
                     'srcipaddr', 'srcipmask', 'dstipaddr', 'dstipmask',
                     'srcipfrom', 'srcipto', 'dstipfrom', 'dstipto',
                     'dscp', 'comment', 'state', 'ipset', 'ipsetflags')

        def __init__(self, virsh_instance=base.base.virsh):
            accessors.XMLAttribute('srcmacaddr', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='srcmacaddr')
            accessors.XMLAttribute('srcmacmask', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='srcmacmask')
            accessors.XMLAttribute('dstmacaddr', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='dstmacaddr')
            accessors.XMLAttribute('dstmacmask', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='dstmacmask')
            accessors.XMLAttribute('srcipaddr', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='srcipaddr')
            accessors.XMLAttribute('srcipmask', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='srcipmask')
            accessors.XMLAttribute('dstipaddr', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='dstipaddr')
            accessors.XMLAttribute('dstipmask', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='dstipmask')
            accessors.XMLAttribute('srcipfrom', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='srcipfrom')
            accessors.XMLAttribute('srcipto', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='srcipto')
            accessors.XMLAttribute('dstipfrom', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='dstipfrom')
            accessors.XMLAttribute('dstipto', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='dstipto')
            accessors.XMLAttribute('dscp', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='dscp')
            accessors.XMLAttribute('comment', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='comment')
            accessors.XMLAttribute('state', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='state')
            accessors.XMLAttribute('ipset', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='ipset')
            accessors.XMLAttribute('ipsetflags', self, parent_xpath='/',
                                   tag_name='all-ipv6', attribute='ipsetflags')

            super(self.__class__, self).__init__(virsh_instance=virsh_instance)
            self.xml = '<all-ipv6/>'
