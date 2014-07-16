"""
icmp protocl support class(es)

http://libvirt.org/formatnwfilter.html#nwfelemsRulesProtoICMP
"""

from virttest.libvirt_xml import accessors, xcepts
from virttest.libvirt_xml.nwfilter_protocols import base


class Icmp(base.TypedDeviceBase):

    """
    Create new Icmp xml instances

    Properties:
        attrs: libvirt_xml.nwfilter_protocols.Icmp.Attr instance
    """

    __slots__ = ('attrs',)

    def __init__(self, type_name='file', virsh_instance=base.base.virsh):
        accessors.XMLElementNest('attrs', self, parent_xpath='/',
                                 tag_name='icmp', subclass=self.Attr,
                                 subclass_dargs={
                                     'virsh_instance': virsh_instance})
        super(Icmp, self).__init__(protocol_tag='icmp', type_name=type_name,
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
        Return icmp attribute dict

        :return: None if no icmp in xml, dict of icmp's attributes.
        """
        try:
            icmp_node = self.xmltreefile.reroot('/icmp')
        except KeyError, detail:
            raise xcepts.LibvirtXMLError(detail)
        node = icmp_node.getroot()
        icmp_attr = dict(node.items())

        return icmp_attr

    class Attr(base.base.LibvirtXMLBase):

        """
        Icmp attribute XML class

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
        type: string, ICMP type
        code: string, ICMP code
        comment: string, text with max. 256 characters
        state: string, comma separated list of NEW,ESTABLISHED,RELATED,INVALID or NONE
        ipset: The name of an IPSet managed outside of libvirt
        ipsetflags: flags for the IPSet; requires ipset attribute
        """

        __slots__ = ('srcmacaddr', 'srcmacmask', 'dstmacaddr', 'dstmacmask',
                     'srcipaddr', 'srcipmask', 'dstipaddr', 'dstipmask',
                     'srcipfrom', 'srcipto', 'dstipfrom', 'dstipto',
                     'type', 'code', 'dscp', 'comment', 'state', 'ipset',
                     'ipsetflags')

        def __init__(self, virsh_instance=base.base.virsh):
            accessors.XMLAttribute('srcmacaddr', self, parent_xpath='/',
                                   tag_name='icmp', attribute='srcmacaddr')
            accessors.XMLAttribute('srcmacmask', self, parent_xpath='/',
                                   tag_name='icmp', attribute='srcmacmask')
            accessors.XMLAttribute('dstmacaddr', self, parent_xpath='/',
                                   tag_name='icmp', attribute='dstmacaddr')
            accessors.XMLAttribute('dstmacmask', self, parent_xpath='/',
                                   tag_name='icmp', attribute='dstmacmask')
            accessors.XMLAttribute('srcipaddr', self, parent_xpath='/',
                                   tag_name='icmp', attribute='srcipaddr')
            accessors.XMLAttribute('srcipmask', self, parent_xpath='/',
                                   tag_name='icmp', attribute='srcipmask')
            accessors.XMLAttribute('dstipaddr', self, parent_xpath='/',
                                   tag_name='icmp', attribute='dstipaddr')
            accessors.XMLAttribute('dstipmask', self, parent_xpath='/',
                                   tag_name='icmp', attribute='dstipmask')
            accessors.XMLAttribute('srcipfrom', self, parent_xpath='/',
                                   tag_name='icmp', attribute='srcipfrom')
            accessors.XMLAttribute('srcipto', self, parent_xpath='/',
                                   tag_name='icmp', attribute='srcipto')
            accessors.XMLAttribute('dstipfrom', self, parent_xpath='/',
                                   tag_name='icmp', attribute='dstipfrom')
            accessors.XMLAttribute('dstipto', self, parent_xpath='/',
                                   tag_name='icmp', attribute='dstipto')
            accessors.XMLAttribute('type', self, parent_xpath='/',
                                   tag_name='icmp', attribute='type')
            accessors.XMLAttribute('code', self, parent_xpath='/',
                                   tag_name='icmp', attribute='code')
            accessors.XMLAttribute('dscp', self, parent_xpath='/',
                                   tag_name='icmp', attribute='dscp')
            accessors.XMLAttribute('comment', self, parent_xpath='/',
                                   tag_name='icmp', attribute='comment')
            accessors.XMLAttribute('state', self, parent_xpath='/',
                                   tag_name='icmp', attribute='state')
            accessors.XMLAttribute('ipset', self, parent_xpath='/',
                                   tag_name='icmp', attribute='ipset')
            accessors.XMLAttribute('ipsetflags', self, parent_xpath='/',
                                   tag_name='icmp', attribute='ipsetflags')

            super(self.__class__, self).__init__(virsh_instance=virsh_instance)
            self.xml = '<icmp/>'
