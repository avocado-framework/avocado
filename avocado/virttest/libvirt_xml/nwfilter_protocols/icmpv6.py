"""
icmpv6 protocl support class(es)

http://libvirt.org/formatnwfilter.html#nwfelemsRulesProtoICMPv6
"""

from virttest.libvirt_xml import accessors, xcepts
from virttest.libvirt_xml.nwfilter_protocols import base


class Icmpv6(base.TypedDeviceBase):

    """
    Create new Icmpv6 xml instances

    Properties:
        attrs: libvirt_xml.nwfilter_protocols.Icmpv6.Attr instance
    """

    __slots__ = ('attrs',)

    def __init__(self, type_name='file', virsh_instance=base.base.virsh):
        accessors.XMLElementNest('attrs', self, parent_xpath='/',
                                 tag_name='icmpv6', subclass=self.Attr,
                                 subclass_dargs={
                                     'virsh_instance': virsh_instance})
        super(Icmpv6, self).__init__(protocol_tag='icmpv6',
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
        Return icmpv6 attribute dict

        :return: None if no icmpv6 in xml, dict of icmpv6's attributes.
        """
        icmpv6_node = self.xmltreefile.reroot('/icmpv6')
        node = icmpv6_node.getroot()
        icmpv6_attr = dict(node.items())

        return icmpv6_attr

    class Attr(base.base.LibvirtXMLBase):

        """
        Icmpv6 attribute XML class

        Properties:

        srcmacaddr: string, MAC address of sender
        srcipaddr: string, Source IPv6 address
        srcipmask: string, Mask applied to source IPv6 address
        dstipaddr: string, Destination IPv6 address
        dstipmask: string, Mask applied to destination IPv6 address
        srcipfrom: string, Start of range of source IP address
        srcipto: string, End of range of source IP address
        dstipfrom: string, Start of range of destination IP address
        dstipto: string, End of range of destination IP address
        type: string, ICMPv6 type
        code: string, ICMPv6 code
        comment: string, text with max. 256 characters
        state: string, comma separated list of NEW,ESTABLISHED,RELATED,INVALID or NONE
        ipset: The name of an IPSet managed outside of libvirt
        ipsetflags: flags for the IPSet; requires ipset attribute
        """

        __slots__ = ('srcmacaddr', 'srcipaddr', 'srcipmask', 'dstipaddr',
                     'dstipmask', 'srcipfrom', 'srcipto', 'dstipfrom',
                     'dstipto', 'type', 'code', 'dscp', 'comment', 'state',
                     'ipset', 'ipsetflags')

        def __init__(self, virsh_instance=base.base.virsh):
            accessors.XMLAttribute('srcmacaddr', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='srcmacaddr')
            accessors.XMLAttribute('srcipaddr', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='srcipaddr')
            accessors.XMLAttribute('srcipmask', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='srcipmask')
            accessors.XMLAttribute('dstipaddr', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='dstipaddr')
            accessors.XMLAttribute('dstipmask', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='dstipmask')
            accessors.XMLAttribute('srcipfrom', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='srcipfrom')
            accessors.XMLAttribute('srcipto', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='srcipto')
            accessors.XMLAttribute('dstipfrom', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='dstipfrom')
            accessors.XMLAttribute('dstipto', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='dstipto')
            accessors.XMLAttribute('type', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='type')
            accessors.XMLAttribute('code', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='code')
            accessors.XMLAttribute('dscp', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='dscp')
            accessors.XMLAttribute('comment', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='comment')
            accessors.XMLAttribute('state', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='state')
            accessors.XMLAttribute('ipset', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='ipset')
            accessors.XMLAttribute('ipsetflags', self, parent_xpath='/',
                                   tag_name='icmpv6', attribute='ipsetflags')

            super(self.__class__, self).__init__(virsh_instance=virsh_instance)
            self.xml = '<icmpv6/>'
