"""
mac protocl support class(es)

http://libvirt.org/formatnwfilter.html#nwfelemsRulesProtoMAC
"""

from virttest.libvirt_xml import accessors, xcepts
from virttest.libvirt_xml.nwfilter_protocols import base


class Mac(base.TypedDeviceBase):

    """
    Create new Mac xml instances

    Properties:
        attrs: libvirt_xml.nwfilter_protocols.Mac.Attr instance
    """

    __slots__ = ('attrs',)

    def __init__(self, type_name='file', virsh_instance=base.base.virsh):
        accessors.XMLElementNest('attrs', self, parent_xpath='/',
                                 tag_name='mac', subclass=self.Attr,
                                 subclass_dargs={
                                     'virsh_instance': virsh_instance})
        super(Mac, self).__init__(protocol_tag='mac', type_name=type_name,
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
        Return mac attribute dict

        :return: None if no mac in xml, dict of mac's attributes.
        """
        try:
            mac_node = self.xmltreefile.reroot('/mac')
        except KeyError, detail:
            raise xcepts.LibvirtXMLError(detail)
        node = mac_node.getroot()
        mac_attr = dict(node.items())

        return mac_attr

    class Attr(base.base.LibvirtXMLBase):

        """
        Mac attribute XML class

        Properties:

        srcmacaddr: string, MAC address of sender
        srcmacmask: string, Mask applied to MAC address of sender
        dstmacaddr: string, MAC address of destination
        dstmacaddr: string, Mask applied to MAC address of destination
        protocolid: string, Layer 3 protocol ID
        comment: string, text with max. 256 characters
        """

        __slots__ = ('srcmacaddr', 'srcmacmask', 'dstmacaddr', 'dstmacmask',
                     'protocolid', 'comment')

        def __init__(self, virsh_instance=base.base.virsh):
            accessors.XMLAttribute('srcmacaddr', self, parent_xpath='/',
                                   tag_name='mac', attribute='srcmacaddr')
            accessors.XMLAttribute('srcmacmask', self, parent_xpath='/',
                                   tag_name='mac', attribute='srcmacmask')
            accessors.XMLAttribute('dstmacaddr', self, parent_xpath='/',
                                   tag_name='mac', attribute='dstmacaddr')
            accessors.XMLAttribute('dstmacmask', self, parent_xpath='/',
                                   tag_name='mac', attribute='dstmacmask')
            accessors.XMLAttribute('protocolid', self, parent_xpath='/',
                                   tag_name='mac', attribute='protocolid')
            accessors.XMLAttribute('comment', self, parent_xpath='/',
                                   tag_name='mac', attribute='comment')

            super(self.__class__, self).__init__(virsh_instance=virsh_instance)
            self.xml = '<mac/>'
