"""
udplite protocl support class(es)

http://libvirt.org/formatnwfilter.html#nwfelemsRulesProtoMisc
"""

from virttest.libvirt_xml import accessors, xcepts
from virttest.libvirt_xml.nwfilter_protocols import base


class Udplite(base.TypedDeviceBase):

    """
    Create new Udplite xml instances

    Properties:
        attrs: libvirt_xml.nwfilter_protocols.Udplite.Attr instance
    """

    __slots__ = ('attrs',)

    def __init__(self, type_name='file', virsh_instance=base.base.virsh):
        accessors.XMLElementNest('attrs', self, parent_xpath='/',
                                 tag_name='udplite', subclass=self.Attr,
                                 subclass_dargs={
                                     'virsh_instance': virsh_instance})
        super(Udplite, self).__init__(protocol_tag='udplite',
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
        Return udplite attribute dict

        :return: None if no udplite in xml, dict of udplite's attributes.
        """
        try:
            udplite_node = self.xmltreefile.reroot('/udplite')
        except KeyError, detail:
            raise xcepts.LibvirtXMLError(detail)
        node = udplite_node.getroot()
        udplite_attr = dict(node.items())

        return udplite_attr

    class Attr(base.base.LibvirtXMLBase):

        """
        Udplite attribute XML class

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
        state: string, comma separated list of NEW,ESTABLISHED,RELATED, INVALID or NONE
        ipset: The name of an IPSet managed outside of libvirt
        ipsetflags: flags for the IPSet; requires ipset attribute
        """

        __slots__ = ('srcmacaddr', 'srcmacmask', 'dstmacaddr', 'dstmacmask',
                     'srcipaddr', 'srcipmask', 'dstipaddr', 'dstipmask',
                     'srcipfrom', 'srcipto', 'dstipfrom', 'dstipto',
                     'dscp', 'comment', 'state', 'ipset', 'ipsetflags')

        def __init__(self, virsh_instance=base.base.virsh):
            accessors.XMLAttribute('srcmacaddr', self, parent_xpath='/',
                                   tag_name='udplite', attribute='srcmacaddr')
            accessors.XMLAttribute('srcmacmask', self, parent_xpath='/',
                                   tag_name='udplite', attribute='srcmacmask')
            accessors.XMLAttribute('dstmacaddr', self, parent_xpath='/',
                                   tag_name='udplite', attribute='dstmacaddr')
            accessors.XMLAttribute('dstmacmask', self, parent_xpath='/',
                                   tag_name='udplite', attribute='dstmacmask')
            accessors.XMLAttribute('srcipaddr', self, parent_xpath='/',
                                   tag_name='udplite', attribute='srcipaddr')
            accessors.XMLAttribute('srcipmask', self, parent_xpath='/',
                                   tag_name='udplite', attribute='srcipmask')
            accessors.XMLAttribute('dstipaddr', self, parent_xpath='/',
                                   tag_name='udplite', attribute='dstipaddr')
            accessors.XMLAttribute('dstipmask', self, parent_xpath='/',
                                   tag_name='udplite', attribute='dstipmask')
            accessors.XMLAttribute('srcipfrom', self, parent_xpath='/',
                                   tag_name='udplite', attribute='srcipfrom')
            accessors.XMLAttribute('srcipto', self, parent_xpath='/',
                                   tag_name='udplite', attribute='srcipto')
            accessors.XMLAttribute('dstipfrom', self, parent_xpath='/',
                                   tag_name='udplite', attribute='dstipfrom')
            accessors.XMLAttribute('dstipto', self, parent_xpath='/',
                                   tag_name='udplite', attribute='dstipto')
            accessors.XMLAttribute('dscp', self, parent_xpath='/',
                                   tag_name='udplite', attribute='dscp')
            accessors.XMLAttribute('comment', self, parent_xpath='/',
                                   tag_name='udplite', attribute='comment')
            accessors.XMLAttribute('state', self, parent_xpath='/',
                                   tag_name='udplite', attribute='state')
            accessors.XMLAttribute('ipset', self, parent_xpath='/',
                                   tag_name='udplite', attribute='ipset')
            accessors.XMLAttribute('ipsetflags', self, parent_xpath='/',
                                   tag_name='udplite', attribute='ipsetflags')

            super(self.__class__, self).__init__(virsh_instance=virsh_instance)
            self.xml = '<udplite/>'
